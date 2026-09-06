"""Redis 滑动窗口限流器及本地测试后备。"""

import asyncio
import time
from collections import defaultdict
from uuid import uuid4

from redis.exceptions import RedisError

from .redis import redis_client


class RateLimitExceeded(RuntimeError):
    """请求超过指定窗口阈值。"""

    def __init__(self, retry_after: int) -> None:
        super().__init__("RATE_LIMITED")
        self.retry_after = retry_after


class SlidingWindowRateLimiter:
    """用 Redis ZSET 原子统计窗口请求数，开发模式使用进程内实现。"""

    def __init__(self) -> None:
        self._fallback: defaultdict[str, list[float]] = defaultdict(list)
        self._fallback_lock = asyncio.Lock()

    async def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        use_redis: bool,
    ) -> None:
        """记录当前请求，超过窗口限制时抛出异常。"""
        if not use_redis:
            await self._check_fallback(key, limit=limit, window_seconds=window_seconds)
            return
        now = time.time()
        redis_key = f"rate_limit:{key}"
        member = f"{now}:{uuid4().hex}"
        try:
            async with redis_client.pipeline(transaction=True) as pipeline:
                pipeline.zremrangebyscore(redis_key, 0, now - window_seconds)
                pipeline.zadd(redis_key, {member: now})
                pipeline.zcard(redis_key)
                pipeline.expire(redis_key, window_seconds)
                results = await pipeline.execute()
            if int(results[2]) > limit:
                raise RateLimitExceeded(window_seconds)
        except RedisError:
            await self._check_fallback(key, limit=limit, window_seconds=window_seconds)

    async def _check_fallback(self, key: str, *, limit: int, window_seconds: int) -> None:
        """在单进程开发和测试环境中执行同等滑动窗口检查。"""
        async with self._fallback_lock:
            now = time.monotonic()
            threshold = now - window_seconds
            active = [timestamp for timestamp in self._fallback[key] if timestamp > threshold]
            active.append(now)
            self._fallback[key] = active
            if len(active) > limit:
                raise RateLimitExceeded(window_seconds)


rate_limiter = SlidingWindowRateLimiter()
