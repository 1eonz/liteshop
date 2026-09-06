"""文件上传签名 HTTP 适配层。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError
from ..schemas.uploads import UploadSignRequest
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.uploads import UploadProviderUnavailable, UploadValidationError, upload_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/sign")
async def sign_upload(
    payload: UploadSignRequest,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等生成十五分钟有效的客户端直传签名。"""

    async def operation(_session: AsyncSession | None) -> IdempotentResult:
        signature = upload_service.sign(payload).as_response()
        return IdempotentResult(signature, "upload_signature", str(signature["fileUrl"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type="upload_sign",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error
    except UploadValidationError as error:
        raise ApiError(
            status_code=400,
            code=40001,
            i18n_key="common.invalid_request",
            message=str(error),
        ) from error
    except UploadProviderUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="对象存储服务暂不可用",
        ) from error
