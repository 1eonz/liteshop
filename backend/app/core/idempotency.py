"""Redis + 数据库双层幂等保护。"""

import asyncio
import time
from dataclasses import dataclass

from redis.exceptions import RedisError

from .config import settings
from .redis import redis_client


@dataclass(frozen=True)
class IdempotencyProbe:
    """描述一次幂等键探测结果。"""

    acquired: bool
    cached_response: str | None


class RedisIdempotencyStore:
    """使用 Redis NX 锁住请求，并在完成后缓存响应五分钟。"""

    pending_value = "__pending__"

    def __init__(self) -> None:
        self._fallback: dict[str, tuple[float, str]] = {}
        self._fallback_lock = asyncio.Lock()

    @staticmethod
    def _text(value: str | bytes | None) -> str | None:
        """兼容 Redis 客户端在不同配置下返回的字符串类型。"""
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else value

    async def probe(self, key: str, *, use_redis: bool = True) -> IdempotencyProbe:
        """探测或占用幂等键；Redis 不可用时降级到数据库唯一键。"""
        if not use_redis:
            return await self._probe_fallback(key)
        try:
            redis_cached = self._text(await redis_client.get(key))
            if redis_cached is not None:
                return IdempotencyProbe(acquired=False, cached_response=redis_cached)
            acquired = await redis_client.set(
                key,
                self.pending_value,
                ex=settings.idempotency_ttl_seconds,
                nx=True,
            )
            if acquired:
                return IdempotencyProbe(acquired=True, cached_response=None)
            return IdempotencyProbe(acquired=False, cached_response=self._text(await redis_client.get(key)))
        except RedisError:
            return await self._probe_fallback(key)

    async def _probe_fallback(self, key: str) -> IdempotencyProbe:
        """Redis 不可用或测试模式时使用进程内原子后备。"""
        async with self._fallback_lock:
            now = time.monotonic()
            fallback_cached = self._fallback.get(key)
            if fallback_cached is not None and fallback_cached[0] > now:
                return IdempotencyProbe(acquired=False, cached_response=fallback_cached[1])
            self._fallback[key] = (now + settings.idempotency_ttl_seconds, self.pending_value)
            return IdempotencyProbe(acquired=True, cached_response=None)

    async def complete(self, key: str, response_json: str, *, use_redis: bool = True) -> None:
        """把已提交的响应写入 Redis，重复请求可直接返回。"""
        if not use_redis:
            async with self._fallback_lock:
                self._fallback[key] = (time.monotonic() + settings.idempotency_ttl_seconds, response_json)
            return
        try:
            await redis_client.set(key, response_json, ex=settings.idempotency_ttl_seconds)
        except RedisError:
            async with self._fallback_lock:
                self._fallback[key] = (time.monotonic() + settings.idempotency_ttl_seconds, response_json)

    async def release(self, key: str, *, use_redis: bool = True) -> None:
        """业务事务失败时释放 pending 标记。"""
        if not use_redis:
            async with self._fallback_lock:
                self._fallback.pop(key, None)
            return
        try:
            await redis_client.delete(key)
        except RedisError:
            async with self._fallback_lock:
                self._fallback.pop(key, None)


idempotency_store = RedisIdempotencyStore()


def make_idempotency_key(user_id: str, request_id: str, action_type: str) -> str:
    """生成用户、请求和动作三元组组成的 Redis 键。"""
    return f"idempotency:{user_id}:{action_type}:{request_id}"
