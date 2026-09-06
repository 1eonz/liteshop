"""Refresh Token 会话登记、轮换和撤销。"""

import asyncio
import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from .config import settings
from .redis import redis_client

_CONSUME_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then
    return false
end
redis.call('DEL', KEYS[1])
return value
"""

_ROTATE_SCRIPT = """
local value = redis.call('GET', KEYS[1])
if not value then
    return 0
end
redis.call('DEL', KEYS[1])
redis.call('SET', KEYS[2], ARGV[1], 'EX', ARGV[2])
return 1
"""


@dataclass(frozen=True)
class RefreshSession:
    """当前有效 refresh token 的最小会话信息。"""

    subject: str
    expires_at: float


class TokenStoreUnavailable(RuntimeError):
    """令牌会话存储不可用。"""


class RefreshTokenStore:
    """用 Redis 或进程内后备存储维护 refresh token 的单次轮换语义。"""

    def __init__(self) -> None:
        self._fallback: dict[str, RefreshSession] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _key(jti: str) -> str:
        return f"auth:refresh:{jti}"

    async def register(self, jti: str, subject: str, ttl_seconds: int) -> None:
        """登记新 refresh token。"""
        if settings.use_database:
            try:
                await redis_client.set(self._key(jti), subject, ex=ttl_seconds)
            except RedisError as exc:
                raise TokenStoreUnavailable("刷新令牌存储暂不可用") from exc
            return
        async with self._lock:
            self._fallback[jti] = RefreshSession(subject, time.monotonic() + ttl_seconds)

    async def consume(self, jti: str, subject: str) -> bool:
        """原子消费旧令牌，只允许一次刷新或撤销操作成功。"""
        if settings.use_database:
            try:
                result = await redis_client.eval(_CONSUME_SCRIPT, 1, self._key(jti))
            except RedisError as exc:
                raise TokenStoreUnavailable("刷新令牌存储暂不可用") from exc
            stored = result.decode() if isinstance(result, bytes) else result
            return bool(stored) and str(stored) == subject
        async with self._lock:
            session = self._fallback.pop(jti, None)
            if session is None or session.expires_at <= time.monotonic():
                return False
            return session.subject == subject

    async def rotate(self, old_jti: str, new_jti: str, subject: str, ttl_seconds: int) -> bool:
        """原子消费旧令牌并登记新令牌，避免并发刷新双成功。"""
        if settings.use_database:
            try:
                result = await redis_client.eval(
                    _ROTATE_SCRIPT,
                    2,
                    self._key(old_jti),
                    self._key(new_jti),
                    subject,
                    ttl_seconds,
                )
            except RedisError as exc:
                raise TokenStoreUnavailable("刷新令牌存储暂不可用") from exc
            return int(result or 0) == 1
        async with self._lock:
            session = self._fallback.get(old_jti)
            if session is None or session.expires_at <= time.monotonic() or session.subject != subject:
                self._fallback.pop(old_jti, None)
                return False
            self._fallback.pop(old_jti, None)
            self._fallback[new_jti] = RefreshSession(subject, time.monotonic() + ttl_seconds)
            return True

    async def revoke(self, jti: str) -> None:
        """撤销当前 refresh token。"""
        if settings.use_database:
            try:
                await redis_client.delete(self._key(jti))
            except RedisError as exc:
                raise TokenStoreUnavailable("刷新令牌存储暂不可用") from exc
            return
        async with self._lock:
            self._fallback.pop(jti, None)


refresh_token_store = RefreshTokenStore()
