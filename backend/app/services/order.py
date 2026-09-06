"""订单状态机与幂等写入服务。"""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..enums.order import ALLOWED_TRANSITIONS, OrderStatus


class InvalidOrderTransition(ValueError):
    """非法订单状态流转。"""


@dataclass
class Order:
    """订单聚合，金额全部使用整数分。"""

    order_id: int
    user_id: str
    total_amount: int
    status: OrderStatus = OrderStatus.PENDING_PAYMENT
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class OrderService:
    """在事务边界内管理订单状态和客户端请求幂等。"""

    def __init__(self) -> None:
        self._orders: dict[int, Order] = {}
        self._requests: dict[tuple[str, str, str], int] = {}

    def create(self, user_id: str, request_id: str, total_amount: int) -> Order:
        """创建订单，重复请求返回原订单。"""
        if total_amount < 0:
            raise ValueError("订单金额不能为负数")
        key = (user_id, request_id, "create_order")
        if key in self._requests:
            return self._orders[self._requests[key]]
        order = Order(order_id=len(self._orders) + 1, user_id=user_id, total_amount=total_amount)
        self._orders[order.order_id] = order
        self._requests[key] = order.order_id
        return order

    def get(self, order_id: int) -> Order:
        """读取内存测试模式订单。"""
        return self._orders[order_id]

    def list_for_user(self, user_id: str, offset: int, limit: int) -> tuple[list[Order], int]:
        """读取内存测试模式下当前用户的订单分页。"""
        items = sorted(
            (order for order in self._orders.values() if order.user_id == user_id),
            key=lambda order: order.created_at,
            reverse=True,
        )
        return items[offset : offset + limit], len(items)

    def transition(self, order_id: int, target: OrderStatus) -> Order:
        """执行合法状态流转，非法流转直接拒绝。"""
        order = self._orders[order_id]
        if target not in ALLOWED_TRANSITIONS[order.status]:
            raise InvalidOrderTransition(f"{order.status}->{target} 不允许")
        order.status = target
        return order
