"""文件上传签名业务服务。"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePath
from uuid import uuid4

from ..core.config import Settings, settings
from ..schemas.uploads import UploadSignRequest


class UploadValidationError(ValueError):
    """上传文件元数据不符合白名单。"""


class UploadProviderUnavailable(RuntimeError):
    """当前对象存储适配器不可用。"""


@dataclass(frozen=True)
class UploadSignature:
    """客户端直传所需参数。"""

    upload_url: str
    method: str
    headers: dict[str, str]
    file_url: str
    thumbnail_url: str
    expires_in: int

    def as_response(self) -> dict[str, object]:
        """转换为 OpenAPI 使用的驼峰字段。"""
        return {
            "uploadUrl": self.upload_url,
            "method": self.method,
            "headers": self.headers,
            "fileUrl": self.file_url,
            "thumbnailUrl": self.thumbnail_url,
            "expiresIn": self.expires_in,
        }


class UploadService:
    """校验上传元数据并为本地开发生成短期签名。"""

    allowed_suffixes = {
        "image/jpeg": {".jpg", ".jpeg"},
        "image/png": {".png"},
        "image/webp": {".webp"},
        "image/gif": {".gif"},
        "application/pdf": {".pdf"},
    }

    def __init__(self, app_settings: Settings = settings) -> None:
        self.settings = app_settings

    def sign(self, payload: UploadSignRequest) -> UploadSignature:
        """生成签名；云厂商模式必须由对应 SDK 适配器接管。"""
        self._validate(payload)
        if self.settings.oss_provider != "local":
            raise UploadProviderUnavailable("当前环境未安装对象存储 SDK")
        file_id = uuid4().hex
        suffix = PurePath(payload.file_name).suffix.lower()
        object_key = f"uploads/{datetime.now(UTC):%Y/%m}/{file_id}{suffix}"
        expires_in = 900
        expires_at = int(datetime.now(UTC).timestamp()) + expires_in
        signature_payload = f"{object_key}:{payload.content_type}:{payload.file_size}:{expires_at}"
        secret = self.settings.oss_access_key_secret or self.settings.jwt_secret
        signature = hmac.new(secret.encode(), signature_payload.encode(), hashlib.sha256).hexdigest()
        base_url = self.settings.oss_cdn_domain.rstrip("/")
        file_url = f"{base_url}/{object_key}"
        return UploadSignature(
            upload_url=file_url,
            method="POST",
            headers={
                "Authorization": f"LiteShop {signature}",
                "Content-Type": payload.content_type,
                "x-oss-meta-uuid": file_id,
                "x-liteshop-expires": str(expires_at),
            },
            file_url=file_url,
            thumbnail_url=f"{file_url}?x-oss-process=image/resize,w_300/format,webp",
            expires_in=expires_in,
        )

    def _validate(self, payload: UploadSignRequest) -> None:
        """校验大小、MIME 与扩展名的组合。"""
        if payload.file_size > self.settings.upload_max_size_bytes:
            raise UploadValidationError("文件大小超过限制")
        if payload.content_type not in self.settings.upload_allowed_mime_types:
            raise UploadValidationError("文件类型不在白名单")
        suffix = PurePath(payload.file_name).suffix.lower()
        if suffix not in self.allowed_suffixes.get(payload.content_type, set()):
            raise UploadValidationError("文件扩展名与内容类型不匹配")


upload_service = UploadService()
