"""页面、导航和营销 API 数据库分支覆盖测试。"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import marketing, navigation, pages
from app.core.config import settings
from app.errors import ApiError
from app.schemas.marketing import CouponClaimRequest, CouponCreate
from app.schemas.navigation import NavigationItemCreate, NavigationItemUpdate
from app.schemas.page import (
    PageConversionEventInput,
    PageCopyInput,
    PageCreateInput,
    PageSchemaInput,
    PageVariantInput,
)
from app.services.admin import AdminPermissionDenied
from app.services.idempotency import IdempotencyInProgress, IdempotentResult
from app.services.marketing import CouponError
from app.services.navigation import NavigationError
from app.services.page import PageSchemaError

SESSION = cast(AsyncSession, object())
type Operation = Callable[[AsyncSession | None], Awaitable[IdempotentResult]]
type Response = dict[str, object]


def response_data(response: Response) -> dict[str, object]:
    """提取并校验统一响应中的 data 对象。"""
    data = response["data"]
    assert isinstance(data, dict)
    return data


def response_value(response: Response) -> object:
    """提取统一响应中的任意 data 载荷。"""
    return response["data"]


def _page_payload() -> PageSchemaInput:
    """构造最小合法页面 Schema。"""
    return PageSchemaInput.model_validate({"slug": "home", "channel": "site", "version": 1, "components": []})


def _coupon_payload() -> CouponCreate:
    """构造最小合法优惠券请求。"""
    starts = datetime.now(UTC)
    return CouponCreate(
        code="WELCOME",
        name="新人券",
        couponType="FULL_REDUCTION",
        thresholdCents=100,
        discountCents=10,
        startsAt=starts,
        endsAt=starts + timedelta(days=1),
    )


def _database_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """让目标 API 进入数据库分支。"""
    configured = replace(settings, use_database=True)
    monkeypatch.setattr(pages, "settings", configured)
    monkeypatch.setattr(navigation, "settings", configured)
    monkeypatch.setattr(marketing, "settings", configured)


def _idempotency_stub(monkeypatch: pytest.MonkeyPatch, module: object, session: AsyncSession) -> None:
    """让幂等包装直接执行一次操作，专注验证 API 编排。"""

    async def execute(**kwargs: object) -> dict[str, object]:
        operation = cast(Operation, kwargs["operation"])
        result = await operation(session)
        return result.response

    monkeypatch.setattr(module, "idempotency_service", SimpleNamespace(execute=execute))


def test_pages_database_success_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """页面数据库分支覆盖查询、写入、发布、变体和事件。"""
    _database_settings(monkeypatch)
    service = SimpleNamespace(
        get_by_slug=AsyncMock(return_value={"id": 1, "slug": "home", "channel": "site", "status": "PUBLISHED"}),
        list_public_pages=AsyncMock(return_value=[]),
        list_pages=AsyncMock(return_value=[]),
        create=AsyncMock(return_value={"id": 2, "slug": "new", "channel": "site"}),
        get=AsyncMock(return_value={"id": 1, "slug": "home", "channel": "site"}),
        save=AsyncMock(return_value={"id": 1, "slug": "home", "channel": "site"}),
        set_home=AsyncMock(return_value={"id": 1, "slug": "home", "channel": "site"}),
        publish=AsyncMock(return_value={"id": 1, "slug": "home", "channel": "site"}),
        copy=AsyncMock(return_value={"id": 3, "slug": "copy", "channel": "site"}),
        remove=AsyncMock(return_value={"deleted": True, "id": 2}),
        list_variants=AsyncMock(return_value=[]),
        save_variant=AsyncMock(return_value={"id": 4, "key": "a", "slug": "home", "channel": "site"}),
        record_event=AsyncMock(return_value={"id": 5, "accepted": True}),
    )
    monkeypatch.setattr(pages, "page_service", service)
    monkeypatch.setattr(pages._admin_service, "require_permission", AsyncMock())
    monkeypatch.setattr(pages, "trigger_isr_revalidate", AsyncMock())
    _idempotency_stub(monkeypatch, pages, SESSION)

    async def run() -> None:
        assert response_data(await pages.get_public_page("home", SESSION))["id"] == 1
        assert response_data(await pages.list_public_pages(SESSION))["items"] == []
        assert response_data(await pages.list_pages("7", SESSION))["items"] == []
        assert (
            response_data(
                await pages.create_page(
                    PageCreateInput.model_validate({"slug": "new", "channel": "site", "version": 1, "components": []}),
                    "7",
                    "r1",
                )
            )["id"]
            == 2
        )
        assert response_data(await pages.get_page_schema(1, SESSION))["id"] == 1
        assert response_data(await pages.save_page_schema(1, _page_payload(), "7", "r2"))["id"] == 1
        assert response_data(await pages.set_home_page(1, "7", "r3"))["id"] == 1
        assert response_data(await pages.publish_page(1, "7", "r4"))["id"] == 1
        assert response_data(await pages.copy_page(1, PageCopyInput(slug="copy"), "7", "r5"))["id"] == 3
        assert response_data(await pages.delete_page(2, "7", "r6"))["deleted"] is True
        assert response_value(await pages.list_page_variants(1, "7", SESSION)) == []
        variant = PageVariantInput(key="a", name="A", schema=_page_payload())
        assert response_data(await pages.save_page_variant(1, "a", variant, "7", "r7"))["id"] == 4
        event = PageConversionEventInput(eventName="view")
        assert response_data(await pages.record_page_event(1, event, "r8"))["accepted"] is True

    asyncio.run(run())
    service.publish.assert_awaited_once()


def test_page_api_maps_domain_and_idempotency_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """页面 API 将领域冲突和幂等处理中转换为统一 ApiError。"""
    _database_settings(monkeypatch)
    service = SimpleNamespace(create=AsyncMock(side_effect=PageSchemaError("冲突")))
    monkeypatch.setattr(pages, "page_service", service)
    monkeypatch.setattr(pages._admin_service, "require_permission", AsyncMock())

    async def raise_in_progress(**_: object) -> dict[str, object]:
        raise IdempotencyInProgress("处理中")

    monkeypatch.setattr(pages, "idempotency_service", SimpleNamespace(execute=raise_in_progress))
    payload = PageCreateInput.model_validate({"slug": "new", "channel": "site", "version": 1, "components": []})
    with pytest.raises(ApiError) as error:
        asyncio.run(pages.create_page(payload, "7", "r1"))
    assert error.value.status_code == 429


def test_navigation_database_success_and_error_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    """导航数据库分支覆盖读写、ISR 和不存在错误。"""
    _database_settings(monkeypatch)
    item = {"id": 1, "label": "产品", "href": "/products"}
    service = SimpleNamespace(
        list_enabled=AsyncMock(return_value=[item]),
        list_admin=AsyncMock(return_value=[item]),
        list_all=AsyncMock(return_value=[item]),
        create=AsyncMock(return_value=item),
        update=AsyncMock(return_value=item),
        remove=AsyncMock(return_value={"deleted": True, "id": 1}),
    )
    monkeypatch.setattr(navigation, "navigation_service", service)
    monkeypatch.setattr(navigation._admin_service, "require_permission", AsyncMock())
    monkeypatch.setattr(navigation, "trigger_isr_revalidate", AsyncMock())
    _idempotency_stub(monkeypatch, navigation, SESSION)

    async def run() -> None:
        assert response_data(await navigation.list_site_navigation("header", SESSION))["items"] == [item]
        assert response_data(await navigation.list_admin_navigation("7", SESSION))["items"] == [item]
        payload = NavigationItemCreate(label="产品", href="/products")
        assert response_data(await navigation.create_navigation(payload, "7", "n1", SESSION))["id"] == 1
        assert (
            response_data(
                await navigation.update_navigation(1, NavigationItemUpdate(label="新产品", href="/new"), "7", "n2")
            )["id"]
            == 1
        )
        assert response_data(await navigation.delete_navigation(1, "7", "n3"))["deleted"] is True

    asyncio.run(run())

    async def missing(**_: object) -> dict[str, object]:
        raise NavigationError("不存在")

    monkeypatch.setattr(navigation, "idempotency_service", SimpleNamespace(execute=missing))
    with pytest.raises(ApiError) as error:
        asyncio.run(navigation.update_navigation(99, NavigationItemUpdate(label="x", href="/x"), "7", "n4"))
    assert error.value.status_code == 404


def test_navigation_and_marketing_permission_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """后台写 API 权限失败时统一返回 403。"""
    _database_settings(monkeypatch)

    async def denied(*_: object, **__: object) -> None:
        raise AdminPermissionDenied("无权限")

    monkeypatch.setattr(navigation._admin_service, "require_permission", denied)
    with pytest.raises(ApiError) as nav_error:
        asyncio.run(navigation.list_admin_navigation("7", SESSION))
    assert nav_error.value.status_code == 403
    monkeypatch.setattr(marketing._admin_service, "require_permission", denied)
    payload = _coupon_payload()

    async def operation(**kwargs: object) -> dict[str, object]:
        callback = cast(Operation, kwargs["operation"])
        return (await callback(SESSION)).response

    monkeypatch.setattr(marketing, "idempotency_service", SimpleNamespace(execute=operation))
    with pytest.raises(ApiError) as coupon_error:
        asyncio.run(marketing.create_coupon(payload, "7", "c1", SESSION))
    assert coupon_error.value.status_code == 403


def test_marketing_database_success_and_domain_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """优惠券列表、领取和创建覆盖数据库成功与领域异常。"""
    _database_settings(monkeypatch)
    service = SimpleNamespace(
        list_coupons=AsyncMock(return_value=[]),
        claim=AsyncMock(return_value={"claimed": True}),
        create_coupon=AsyncMock(return_value={"id": 1, "code": "WELCOME"}),
    )
    monkeypatch.setattr(marketing, "marketing_service", service)
    monkeypatch.setattr(marketing._admin_service, "require_permission", AsyncMock())
    _idempotency_stub(monkeypatch, marketing, SESSION)

    async def run() -> None:
        assert response_data(await marketing.list_coupons(SESSION))["items"] == []
        assert (
            response_data(await marketing.claim_coupon(CouponClaimRequest(couponCode="WELCOME"), "7", "c1"))["claimed"]
            is True
        )
        assert response_data(await marketing.create_coupon(_coupon_payload(), "7", "c2", SESSION))["id"] == 1

    asyncio.run(run())

    async def unavailable(**_: object) -> dict[str, object]:
        raise CouponError("不可用")

    monkeypatch.setattr(marketing, "idempotency_service", SimpleNamespace(execute=unavailable))
    with pytest.raises(ApiError) as error:
        asyncio.run(marketing.claim_coupon(CouponClaimRequest(couponCode="WELCOME"), "7", "c3"))
    assert error.value.status_code == 409
