"""订单 API 的领域路由模块。"""

from .callbacks import router as callbacks_router
from .freight import router as freight_router
from .order_commands import router as commands_router
from .order_queries import router as queries_router
from .payments import router as payments_router
from .refunds import router as refunds_router

__all__ = [
    "callbacks_router",
    "commands_router",
    "freight_router",
    "queries_router",
    "payments_router",
    "refunds_router",
]
