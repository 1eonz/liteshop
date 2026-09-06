"""基础设施就绪探针。"""

import asyncio

from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import settings
from .database import engine
from .redis import redis_client

PROBE_TIMEOUT_SECONDS = 2


async def check_database() -> bool:
    """验证 PostgreSQL 能执行最小查询。"""
    try:
        async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        return True
    except (TimeoutError, OSError, SQLAlchemyError):
        return False


async def check_redis() -> bool:
    """验证 Redis PING。"""
    try:
        async with asyncio.timeout(PROBE_TIMEOUT_SECONDS):
            return bool(await redis_client.ping())
    except (TimeoutError, OSError, RedisError):
        return False


async def check_object_storage() -> bool:
    """验证当前对象存储适配器具备可用配置。"""
    if settings.oss_provider == "local":
        return bool(settings.oss_cdn_domain)
    return False


async def readiness_checks() -> dict[str, bool]:
    """并行运行所有基础设施检查。"""
    database, redis, object_storage = await asyncio.gather(
        check_database(),
        check_redis(),
        check_object_storage(),
    )
    return {"database": database, "redis": redis, "objectStorage": object_storage}
