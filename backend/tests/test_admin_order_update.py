"""后台订单地址编辑的状态与字段校验测试。"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.order import OrderStatus
from app.schemas.admin import OrderManagementUpdate
from app.services.admin import AdminService
from app.services.order_workflow import OrderWorkflow, OrderWorkflowError

VALID_ADDRESS = {
    "receiverName": "测试用户",
    "phone": "13800000000",
    "detail": "杭州市西湖区文三路 1 号",
}


def _order(status: OrderStatus) -> SimpleNamespace:
    """构造仅包含订单响应所需字段的测试订单。"""
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=1,
        order_no="LS202609080001",
        status=status.value,
        total_amount=100,
        product_amount=100,
        freight_amount=0,
        discount_amount=0,
        refund_status="NONE",
        paid_amount=None,
        address_snapshot=dict(VALID_ADDRESS),
        remark=None,
        paid_at=None,
        shipped_at=None,
        completed_at=None,
        cancelled_at=None,
        cancel_reason=None,
        created_at=now,
        shipping_company_code="",
        tracking_no="",
        items=[],
        updated_at=now,
    )


def _service(order: SimpleNamespace) -> AdminService:
    service = AdminService()
    service.orders = cast(
        OrderWorkflow,
        SimpleNamespace(orders=SimpleNamespace(get_for_update=AsyncMock(return_value=order), flush=AsyncMock())),
    )
    return service


@pytest.mark.parametrize("status", [OrderStatus.SHIPPED, OrderStatus.COMPLETED, OrderStatus.CANCELLED])
def test_address_update_rejects_terminal_or_shipped_orders(
    status: OrderStatus, monkeypatch: pytest.MonkeyPatch
) -> None:
    """已发货、已完成和已取消订单不能修改地址快照。"""
    order = _order(status)
    service = _service(order)
    monkeypatch.setattr(AdminService, "audit", AsyncMock())

    with pytest.raises(OrderWorkflowError, match="只有待付款或已支付订单"):
        asyncio.run(
            service.update_order(
                cast(AsyncSession, AsyncMock()),
                1,
                OrderManagementUpdate(addressSnapshot=VALID_ADDRESS),
                "1",
                "request-address",
            )
        )
    assert order.address_snapshot == VALID_ADDRESS


@pytest.mark.parametrize("status", [OrderStatus.PENDING_PAYMENT, OrderStatus.PAID])
def test_address_update_allows_pending_and_paid_orders(status: OrderStatus, monkeypatch: pytest.MonkeyPatch) -> None:
    """待付款和已支付订单可以更新完整地址快照。"""
    order = _order(status)
    service = _service(order)
    monkeypatch.setattr(AdminService, "audit", AsyncMock())
    updated = {**VALID_ADDRESS, "receiverName": "新收货人"}

    asyncio.run(
        service.update_order(
            cast(AsyncSession, AsyncMock()),
            1,
            OrderManagementUpdate(addressSnapshot=updated),
            "1",
            "request-address",
        )
    )
    assert order.address_snapshot == updated
    cast(AsyncMock, service.orders.orders.flush).assert_awaited_once()


@pytest.mark.parametrize(
    "address",
    [
        {"receiverName": "测试用户", "phone": "13800000000"},
        {"receiverName": "测试用户", "phone": "abc123456", "detail": "详细地址"},
        {"receiverName": "测试用户", "phone": "1-----", "detail": "详细地址"},
        {"receiverName": "", "phone": "13800000000", "detail": "详细地址"},
        {"receiverName": "测试用户", "phone": "13800000000", "detail": "x" * 501},
    ],
)
def test_address_snapshot_rejects_invalid_fields(address: dict[str, str]) -> None:
    """地址快照缺字段、手机号格式错误或超长时由请求 DTO 拒绝。"""
    with pytest.raises(ValidationError):
        OrderManagementUpdate(addressSnapshot=address)
