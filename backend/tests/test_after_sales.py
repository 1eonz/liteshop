"""售后状态机、金额边界与幂等回归测试。"""

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums.after_sale import AfterSaleStatus, AfterSaleType
from app.models.after_sale import AfterSale
from app.repositories.after_sale import AfterSaleRepository
from app.schemas.after_sale import AfterSaleCreate
from app.services.after_sale import AfterSaleError, AfterSaleService


class FakeSession:
    """只实现售后服务单测需要的异步会话方法。"""

    async def scalar(self, _statement: object) -> object | None:
        return None

    async def flush(self) -> None:
        return None


class FakeAfterSaleRepository:
    """提供订单项与售后创建结果，避免单测依赖数据库。"""

    def __init__(self, item: object | None, existing: AfterSale | None = None) -> None:
        self.item = item
        self.existing = existing
        self.created: AfterSale | None = None

    async def get_by_request(self, _session: object, _user_id: int, _request_id: str) -> AfterSale | None:
        return self.existing

    async def get_order_item_for_user(self, _session: object, _order_item_id: int, _user_id: int) -> object | None:
        return self.item

    async def get_for_update(self, _session: object, _after_sale_id: int) -> AfterSale | None:
        return self.existing

    async def create(
        self,
        _session: object,
        *,
        item: object,
        user_id: int,
        request_id: str,
        sale_type: str,
        amount_cents: int,
        reason: str,
        evidence_urls: list[str],
    ) -> AfterSale:
        self.created = AfterSale(
            id=1,
            after_sale_no="AS-TEST-1",
            order_id=7,
            order_item_id=cast(int, cast(SimpleNamespace, item).id),
            user_id=user_id,
            type=sale_type,
            status=AfterSaleStatus.PENDING_REVIEW.value,
            amount_cents=amount_cents,
            reason=reason,
            evidence_urls=evidence_urls,
            client_request_id=request_id,
            created_at=SimpleNamespace(isoformat=lambda: "2026-09-08T00:00:00+00:00"),
            updated_at=SimpleNamespace(isoformat=lambda: "2026-09-08T00:00:00+00:00"),
        )
        return self.created


def _payload(amount_cents: int = 12900) -> AfterSaleCreate:
    """构造有效售后输入。"""
    return AfterSaleCreate(
        order_item_id=11,
        type=AfterSaleType.REFUND_ONLY,
        amount_cents=amount_cents,
        reason="商品存在瑕疵",
    )


def _service(
    item: object | None, existing: AfterSale | None = None
) -> tuple[AfterSaleService, FakeAfterSaleRepository]:
    """构造带假仓储的售后服务。"""
    repository = FakeAfterSaleRepository(item, existing)
    return AfterSaleService(repository=cast(AfterSaleRepository, repository)), repository


def test_create_rejects_missing_order_or_wrong_owner() -> None:
    """订单项不存在时不能创建售后，避免越权申请。"""
    service, _ = _service(None)
    with pytest.raises(AfterSaleError, match="已支付或已发货"):
        asyncio.run(service.create(cast(AsyncSession, FakeSession()), 99, "request-1", _payload()))


def test_create_rejects_amount_above_order_item_total() -> None:
    """售后金额必须小于等于订单项金额。"""
    item = SimpleNamespace(id=11, total_amount=1000, order=SimpleNamespace(status="PAID"))
    service, _ = _service(item)
    with pytest.raises(AfterSaleError, match="不能超过订单项金额"):
        asyncio.run(service.create(cast(AsyncSession, FakeSession()), 1, "request-1", _payload(1001)))


def test_create_returns_existing_request_without_duplicate() -> None:
    """同一用户和请求 ID 直接返回已创建售后单。"""
    existing = cast(AfterSale, SimpleNamespace(id=42))
    service, repository = _service(SimpleNamespace(), existing)
    result = asyncio.run(service.create(cast(AsyncSession, FakeSession()), 1, "request-1", _payload()))
    assert result.id == existing.id
    assert repository.created is None


def test_create_rejects_unfinished_duplicate_for_same_order_item() -> None:
    """同一订单项已有进行中售后时拒绝第二笔申请。"""
    item = SimpleNamespace(id=11, total_amount=12900, order=SimpleNamespace(status="COMPLETED"))

    class ActiveSession(FakeSession):
        async def scalar(self, _statement: object) -> object | None:
            return 99

    service, _ = _service(item)
    with pytest.raises(AfterSaleError, match="进行中的售后申请"):
        asyncio.run(service.create(cast(AsyncSession, ActiveSession()), 1, "request-1", _payload()))


def test_state_machine_rejects_illegal_transition() -> None:
    """已完成售后不能再次回到退款中。"""
    item = AfterSale(
        id=1,
        after_sale_no="AS-TEST-1",
        order_id=7,
        order_item_id=11,
        user_id=1,
        type=AfterSaleType.REFUND_ONLY.value,
        status=AfterSaleStatus.COMPLETED.value,
        amount_cents=100,
        reason="测试",
        evidence_urls=[],
        client_request_id="request-1",
        created_at=SimpleNamespace(),
        updated_at=SimpleNamespace(),
    )
    with pytest.raises(AfterSaleError, match="不允许"):
        AfterSaleService._transition(item, AfterSaleStatus.REFUNDING)


def test_submit_return_requires_waiting_return_state() -> None:
    """仅待寄回状态允许提交物流，避免重复推进状态。"""
    item = AfterSale(
        id=1,
        after_sale_no="AS-TEST-1",
        order_id=7,
        order_item_id=11,
        user_id=1,
        type=AfterSaleType.RETURN_REFUND.value,
        status=AfterSaleStatus.RETURNED.value,
        amount_cents=100,
        reason="测试",
        evidence_urls=[],
        client_request_id="request-1",
        created_at=SimpleNamespace(),
        updated_at=SimpleNamespace(),
    )
    service, repository = _service(SimpleNamespace(), item)
    with pytest.raises(AfterSaleError, match="不需要提交退货"):
        asyncio.run(service.submit_return(cast(AsyncSession, FakeSession()), 1, 1, "SF123"))
    assert repository.created is None


def test_create_accepts_completed_order_item_with_integer_amount() -> None:
    """已完成订单仍可申请售后，且响应保留整数分金额。"""
    item = SimpleNamespace(id=11, total_amount=12900, order=SimpleNamespace(status="COMPLETED"))
    service, repository = _service(item)
    result = asyncio.run(service.create(cast(AsyncSession, FakeSession()), 1, "request-1", _payload(12900)))
    assert result.amount_cents == 12900
    assert result.type == AfterSaleType.REFUND_ONLY.value
    assert repository.created is result


def test_list_for_admin_delegates_through_service_boundary() -> None:
    """后台列表读取必须经过售后服务边界。"""
    items = [cast(AfterSale, SimpleNamespace(id=1))]
    repository = SimpleNamespace(list_all=AsyncMock(return_value=items))
    service = AfterSaleService(repository=cast(AfterSaleRepository, repository))
    result = asyncio.run(service.list_for_admin(cast(AsyncSession, AsyncMock()), "PENDING_REVIEW"))
    assert result == items
    repository.list_all.assert_awaited_once()
