"""订单与支付 API 兼容聚合入口。

领域实现位于 ``order_routes`` 子包；本模块保留原有 ``router`` 和处理函数导出，
因此应用入口、测试及外部集成无需修改。
"""

from fastapi import APIRouter

from .order_routes.callbacks import (
    alipay_callback,
    handle_payment_callback,
    payment_callback,
    wechat_callback,
)
from .order_routes.callbacks import (
    router as callbacks_router,
)
from .order_routes.common import database_user_id, refund_service, require_session, session_dependency, workflow
from .order_routes.freight import calculate_freight
from .order_routes.freight import router as freight_router
from .order_routes.order_commands import (
    cancel_order,
    change_order_status,
    confirm_order,
)
from .order_routes.order_commands import (
    router as commands_router,
)
from .order_routes.order_queries import collection_router, create_order, detail_router, get_order, list_orders
from .order_routes.payments import create_payment
from .order_routes.payments import router as payments_router
from .order_routes.refunds import create_refund
from .order_routes.refunds import router as refunds_router

__all__ = [
    "alipay_callback",
    "calculate_freight",
    "cancel_order",
    "confirm_order",
    "create_order",
    "create_payment",
    "create_refund",
    "get_order",
    "list_orders",
    "payment_callback",
    "refund_service",
    "router",
    "wechat_callback",
    "workflow",
]

# 保持旧文件的注册顺序，确保静态运费路径优先于订单 ID 动态路径。
router = APIRouter(tags=["orders"])
router.include_router(collection_router)
router.include_router(freight_router)
router.include_router(detail_router)
router.include_router(commands_router)
router.include_router(payments_router)
router.include_router(refunds_router)
router.include_router(callbacks_router)

# 私有别名用于兼容可能直接引用旧模块辅助函数的本地集成。
_change_order_status = change_order_status
_database_user_id = database_user_id
_payment_callback = handle_payment_callback
_require_session = require_session
_session_dependency = session_dependency
