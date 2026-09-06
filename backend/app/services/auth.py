"""短信验证码与用户登录服务。"""

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


class AuthService:
    """处理短信验证码和 token 签发。"""

    development_code = "123456"

    def __init__(self, users: UserRepository | None = None) -> None:
        self.users = users or UserRepository()

    async def send_sms_code(self, phone: str) -> None:
        """发送并保存五分钟验证码；限流由 HTTP 适配层统一执行。"""
        if not settings.use_database:
            return
        try:
            await redis_client.set(f"sms:code:{phone}", self.development_code, ex=300)
        except RedisError as exc:
            raise SmsUnavailable("短信服务暂不可用") from exc

    async def verify_sms_code(self, phone: str, code: str) -> None:
        """使用 Redis 原子脚本校验并消费一次性验证码。"""
        if not settings.use_database:
            if code != self.development_code:
                raise AuthenticationError("INVALID_CODE")
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
