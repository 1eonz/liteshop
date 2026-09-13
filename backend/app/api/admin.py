"""管理后台 API 聚合入口。

领域路由位于 ``admin_routes`` 子包；本模块保留原有 ``router`` 导出，
因此应用入口和外部集成无需修改。
"""

from fastapi import APIRouter

from .admin_routes.access import router as access_router
from .admin_routes.catalog import router as catalog_router
from .admin_routes.common import admin_service, authorize_read, execute_write, require_database
from .admin_routes.freight import router as freight_router
from .admin_routes.members_reviews import router as members_reviews_router
from .admin_routes.trade import router as trade_router

__all__ = ["admin_service", "authorize_read", "execute_write", "require_database", "router"]

router = APIRouter(prefix="/admin", tags=["admin"])
router.include_router(catalog_router)
router.include_router(trade_router)
router.include_router(members_reviews_router)
router.include_router(access_router)
router.include_router(freight_router)
