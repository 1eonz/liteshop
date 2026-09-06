"""存活与就绪检查接口。"""

from datetime import UTC, datetime

from fastapi import APIRouter, Response

from ..core.health import readiness_checks

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """返回进程存活状态，不访问外部依赖。"""
    return {"status": "ok"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    """检查 PostgreSQL、Redis 和对象存储适配器。"""
    checks = await readiness_checks()
    all_ready = all(checks.values())
    response.status_code = 200 if all_ready else 503
    return {
        "status": "ok" if all_ready else "degraded",
        "checks": checks,
        "timestamp": datetime.now(UTC).isoformat(),
    }
