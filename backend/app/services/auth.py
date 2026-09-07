"""短信验证码与用户登录服务。"""

import secrets
import time
from collections.abc import Callable
from typing import Protocol

import structlog
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.redis import redis_client
from ..core.security import create_access_token, create_refresh_token, verify_refresh_token_claims
from ..core.token_store import TokenStoreUnavailable, refresh_token_store
from ..enums.user import UserStatus
from ..repositories.user import UserRepository


class AuthenticationError(ValueError):
    """验证码或用户状态不合法。"""


class SmsUnavailable(RuntimeError):
    """短信验证码存储暂不可用。"""


class SmsProvider(Protocol):
    """短信渠道适配器协议。"""

    async def send(self, phone: str, code: str) -> None:
        """向手机号发送验证码。"""


class ConsoleSmsProvider:
    """开发环境短信适配器，只写结构化日志，不向 API 返回验证码。"""

    async def send(self, phone: str, code: str) -> None:
        """把验证码输出到开发日志，便于本地联调。"""
        structlog.get_logger(__name__).info("sms_code_sent", phone=phone, code=code, provider="console")


class UnsupportedSmsProvider:
    """尚未配置凭据的生产短信渠道。"""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def send(self, phone: str, code: str) -> None:
        """拒绝发送，避免未配置渠道时假装发送成功。"""
        del phone, code
        raise SmsUnavailable(f"短信 Provider {self.provider} 尚未配置")


class AuthService:
    """处理短信验证码和 token 签发。"""

    def __init__(
        self,
        users: UserRepository | None = None,
        sms_provider: SmsProvider | None = None,
        code_generator: Callable[[], str] | None = None,
    ) -> None:
        self.users = users or UserRepository()
        self.sms_provider = sms_provider or self._configured_provider()
        self.code_generator = code_generator or self._new_code
        self._memory_codes: dict[str, tuple[str, float]] = {}

    @staticmethod
    def _new_code() -> str:
        """生成不可预测的六位数字验证码。"""
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _configured_provider() -> SmsProvider:
        """按配置选择短信渠道；开发默认使用控制台渠道。"""
        provider = getattr(settings, "sms_provider", "console").strip().lower()
        if provider == "console":
            return ConsoleSmsProvider()
        return UnsupportedSmsProvider(provider)

    async def send_sms_code(self, phone: str) -> None:
        """发送并保存五分钟验证码；限流由 HTTP 适配层统一执行。"""
        code = self.code_generator()
        if len(code) != 6 or not code.isdigit():
            raise SmsUnavailable("验证码生成器返回了无效值")
        try:
            if settings.use_database:
                await redis_client.set(f"sms:code:{phone}", code, ex=300)
            else:
                self._memory_codes[phone] = (code, time.monotonic() + 300)
        except RedisError as exc:
            raise SmsUnavailable("短信服务暂不可用") from exc
        try:
            await self.sms_provider.send(phone, code)
        except SmsUnavailable:
            await self._discard_code(phone)
            raise

    async def _discard_code(self, phone: str) -> None:
        """渠道发送失败时删除已保存验证码，避免留下不可达凭据。"""
        if not settings.use_database:
            self._memory_codes.pop(phone, None)
            return
        try:
            await redis_client.delete(f"sms:code:{phone}")
        except RedisError:
            structlog.get_logger(__name__).exception("sms_code_cleanup_failed", phone=phone)

    async def verify_sms_code(self, phone: str, code: str) -> None:
        """使用 Redis 原子脚本校验并消费一次性验证码。"""
        if not settings.use_database:
            stored = self._memory_codes.get(phone)
            if stored is None or stored[1] <= time.monotonic() or stored[0] != code:
                raise AuthenticationError("INVALID_CODE")
            self._memory_codes.pop(phone, None)
            return
        try:
            stored = await redis_client.eval(
                """
                local value = redis.call('GET', KEYS[1])
                if not value then
                    return false
                end
                redis.call('DEL', KEYS[1])
                return value
                """,
                1,
                f"sms:code:{phone}",
            )
            stored_text = stored.decode() if isinstance(stored, bytes) else stored
            if stored_text != code:
                raise AuthenticationError("INVALID_CODE")
        except RedisError as exc:
            raise SmsUnavailable("短信服务暂不可用") from exc

    async def login(
        self,
        session: AsyncSession | None,
        phone: str,
        code: str,
    ) -> tuple[str, str, str]:
        """校验验证码，创建或更新用户并签发 access/refresh token。"""
        await self.verify_sms_code(phone, code)
        subject = phone
        if settings.use_database:
            if session is None:
                raise RuntimeError("数据库事务会话未初始化")
            user = await self.users.get_or_create_by_phone(session, phone)
            if user.status != UserStatus.ACTIVE.value:
                raise AuthenticationError("USER_DISABLED")
            else:
                await self.users.touch_login(session, user)
            subject = str(user.id)
        access_token = create_access_token(subject)
        refresh_token = create_refresh_token(subject)
        claims = verify_refresh_token_claims(refresh_token)
        if claims is None:
            raise TokenStoreUnavailable("刷新令牌生成失败")
        await refresh_token_store.register(
            claims.jti,
            claims.subject,
            settings.refresh_token_expire_days * 24 * 60 * 60,
        )
        return subject, access_token, refresh_token


auth_service = AuthService()
