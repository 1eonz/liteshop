"""异步 Redis 客户端工厂。"""

from redis.asyncio import Redis

from .config import settings


def create_redis() -> Redis:
    """创建共享 Redis 客户端，连接参数只来自环境配置。"""
    return Redis.from_url(settings.redis_url, decode_responses=True)


redis_client = create_redis()
