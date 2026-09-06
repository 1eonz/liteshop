"""开发环境领域服务容器，生产环境替换为数据库仓储实现。"""

from ..services.inventory import InventoryService
from ..services.order import OrderService
from ..services.payment import PaymentService
from .config import settings

inventory_service = InventoryService()
inventory_service.seed(1, 100)
order_service = OrderService()
payment_service = PaymentService(order_service, settings.payment_callback_secret)
