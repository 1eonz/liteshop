"""后台、用户、运费和退款仓储的分支覆盖测试。"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors.domain import AddressNotFound
from app.models.freight import FreightTemplate, FreightTemplateItem
from app.models.order import Payment
from app.models.refund import Refund
from app.models.user import Address, Role, User
from app.repositories.admin import AdminRepository
from app.repositories.freight import FreightRepository
from app.repositories.refund import RefundRepository
from app.repositories.user import UserRepository

SESSION = cast(AsyncSession, object())


class _Result:
    """模拟 SQLAlchemy ScalarResult，支持唯一化和首项读取。"""

    def __init__(self, values: list[object]) -> None:
        self.values = values

    def all(self) -> list[object]:
        """返回结果列表。"""
        return self.values

    def first(self) -> object | None:
        """返回第一条结果。"""
        return self.values[0] if self.values else None

    def unique(self) -> "_Result":
        """兼容关系预加载查询。"""
        return self


def test_admin_repository_queries_and_mutations() -> None:
    """后台统计、RBAC 查询和角色写操作均委托给会话。"""
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[1, 2, 5_000, 2, 3, 1, SimpleNamespace(id=3), 4])
    session.execute = AsyncMock(
        side_effect=[_Result([("商品 A", 4)]), _Result([(datetime(2026, 9, 12, tzinfo=UTC), 500, 2)])]
    )
    session.scalars = AsyncMock(
        side_effect=[
            _Result([SimpleNamespace(id=1)]),
            _Result([SimpleNamespace(id=2)]),
            _Result([SimpleNamespace(id=3)]),
            _Result([SimpleNamespace(id=2)]),
            _Result([SimpleNamespace(id=4)]),
            _Result([SimpleNamespace(id=5)]),
            _Result([SimpleNamespace(id=6)]),
            _Result([SimpleNamespace(id=7)]),
        ]
    )
    session.add = Mock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    repository = AdminRepository()

    async def run() -> None:
        assert await repository.has_permission(session, 1, "orders.read") is True
        dashboard = await repository.dashboard(session)
        assert dashboard["metrics"] == {
            "salesAmount": 5_000,
            "orderCount": 2,
            "productCount": 3,
            "pendingShipmentCount": 2,
        }
        assert dashboard["ranking"] == [{"name": "商品 A", "salesCount": 4}]
        assert dashboard["trend"] == [{"date": "2026-09-12", "amount": 500, "orderCount": 2}]
        assert len(await repository.list_audit_logs(session, 10)) == 1
        assert len(await repository.list_roles(session)) == 1
        assert len(await repository.list_permissions(session)) == 1
        role_for_update = await repository.get_role(session, 2, for_update=True)
        assert role_for_update is not None and role_for_update.id == 2
        role_by_name = await repository.get_role_by_name(session, "运营")
        assert role_by_name is not None and role_by_name.id == 3
        assert await repository.get_permissions_by_codes(session, []) == []
        assert len(await repository.get_permissions_by_codes(session, ["orders.read"])) == 1
        assert await repository.count_role_users(session, 2) == 4
        user_with_roles = await repository.get_user_with_roles(session, 3, for_update=True)
        assert user_with_roles is not None and user_with_roles.id == 5
        assert await repository.list_roles_by_ids(session, []) == []
        assert len(await repository.list_roles_by_ids(session, [2])) == 1
        assert len(await repository.list_users_with_roles(session)) == 1
        role = cast(Role, SimpleNamespace(id=9))
        assert await repository.add_role(session, role) is role
        await repository.delete_role(session, role)
        await repository.flush(session)
        session.add.assert_called_once_with(role)
        session.delete.assert_awaited_once_with(role)

    asyncio.run(run())


class _NestedTransaction:
    """支持用户仓储保存点测试的异步上下文。"""

    async def __aenter__(self) -> "_NestedTransaction":
        """进入保存点。"""
        return self

    async def __aexit__(self, _type: object, _value: object, _traceback: object) -> None:
        """退出保存点。"""


def test_user_repository_crud_and_unique_phone_recovery() -> None:
    """用户地址 CRUD、默认地址切换及并发手机号冲突恢复。"""
    user = cast(User, SimpleNamespace(id=7, phone="13800000000"))
    address = cast(Address, SimpleNamespace(id=8, user_id=7, is_default=True, created_at=datetime.now(UTC)))
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[user, user, address])
    session.scalars = AsyncMock(return_value=_Result([address]))
    session.get = AsyncMock(return_value=user)
    session.add = Mock()
    session.delete = AsyncMock()
    session.flush = AsyncMock()
    session.execute = AsyncMock()
    session.begin_nested = Mock(return_value=_NestedTransaction())
    repository = UserRepository()

    async def run() -> None:
        by_phone = await repository.get_by_phone(session, user.phone)
        assert by_phone is user
        fetched_user = await repository.get(session, 7)
        assert fetched_user is user
        created = await repository.create(session, "13900000000")
        assert created.phone == "13900000000"
        assert await repository.get_or_create_by_phone(session, "13800000000") is user
        assert await repository.list_addresses(session, 7) == [address]
        locked_address = await repository.get_address_for_update(session, 7, 8)
        assert locked_address is address
        await repository.clear_default_address(session, 7)
        assert await repository.add_address(session, address) is address
        await repository.flush(session)
        await repository.delete_address(session, address)

    asyncio.run(run())
    session.execute.assert_awaited_once()
    session.delete.assert_awaited_once_with(address)


def test_user_repository_get_or_create_recovers_integrity_error() -> None:
    """手机号唯一键竞争时从保存点回滚并读回已提交用户。"""
    session = AsyncMock()
    recovered_user = cast(User, SimpleNamespace(id=10, phone="13800000000"))
    session.scalar = AsyncMock(side_effect=[None, recovered_user])
    session.begin_nested = Mock(return_value=_NestedTransaction())
    repository = UserRepository()
    create_mock = AsyncMock(side_effect=IntegrityError("insert", {}, Exception("duplicate")))
    repository.__dict__["create"] = create_mock

    recovered = asyncio.run(repository.get_or_create_by_phone(session, "13800000000"))
    assert recovered.id == 10
    create_mock.assert_awaited_once_with(session, "13800000000")


def test_user_repository_missing_address_raises_domain_error() -> None:
    """锁定不属于当前用户或不存在的地址时返回统一领域错误。"""
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=None)
    with pytest.raises(AddressNotFound):
        asyncio.run(UserRepository().get_address_for_update(session, 7, 404))


def test_freight_repository_queries_and_mutations() -> None:
    """运费模板及计费项仓储覆盖查询、默认清理和增删改。"""
    template = cast(FreightTemplate, SimpleNamespace(id=1, items=[]))
    item = cast(FreightTemplateItem, SimpleNamespace(id=2, template_id=1))
    session = AsyncMock()
    session.scalars = AsyncMock(side_effect=[_Result([template]), _Result([template])])
    session.scalar = AsyncMock(side_effect=[template, item])
    session.add = Mock()
    session.delete = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    repository = FreightRepository()

    async def run() -> None:
        assert await repository.list_templates(session) == [template]
        fetched_template = await repository.get_template(session, 1, for_update=True)
        assert fetched_template is template
        default_template = await repository.get_default_template(session)
        assert default_template is template
        await repository.clear_default(session)
        await repository.clear_default(session, except_id=1)
        assert await repository.add_template(session, template) is template
        await repository.flush(session)
        await repository.delete_template(session, template)
        assert await repository.add_item(session, item) is item
        fetched_item = await repository.get_item(session, 1, 2)
        assert fetched_item is item
        await repository.delete_item(session, item)

    asyncio.run(run())
    assert session.execute.await_count == 2
    session.delete.assert_any_await(template)
    session.delete.assert_awaited_with(item)


def test_refund_repository_queries_and_create() -> None:
    """退款仓储覆盖请求幂等查询、金额汇总、锁定和创建。"""
    payment = cast(Payment, SimpleNamespace(id=4))
    refund = cast(Refund, SimpleNamespace(id=5))
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[refund, 1250])
    session.get = AsyncMock(return_value=refund)
    session.add = Mock()
    session.flush = AsyncMock()
    repository = RefundRepository()

    async def run() -> None:
        assert await repository.get_by_request(session, 4, "req") is refund
        assert await repository.get_for_update(session, 5) is refund
        assert await repository.sum_active_amount(session, 4) == 1250
        await repository.flush(session)
        created = await repository.create(
            session, payment=payment, amount_cents=500, reason="商品问题", request_id="req-2"
        )
        assert created.amount_cents == 500
        assert created.status == "PENDING"

    asyncio.run(run())
    session.add.assert_called_once()
    session.flush.assert_awaited()
