"""滑动窗口限流测试。"""

import asyncio

import pytest

from app.core.rate_limit import RateLimitExceeded, SlidingWindowRateLimiter


def test_fallback_sliding_window_rejects_excess_request() -> None:
    """本地后备与 Redis 模式使用相同的窗口阈值语义。"""
    limiter = SlidingWindowRateLimiter()
    asyncio.run(limiter.check("test-key", limit=2, window_seconds=60, use_redis=False))
    asyncio.run(limiter.check("test-key", limit=2, window_seconds=60, use_redis=False))
    with pytest.raises(RateLimitExceeded):
        asyncio.run(limiter.check("test-key", limit=2, window_seconds=60, use_redis=False))
