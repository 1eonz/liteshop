"""核心领域服务分支和错误路径测试。"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freight import FreightTemplate, FreightTemplateItem
from app.models.page import PageVariant, StorePage
from app.models.user import Address, User
from app.repositories.freight import FreightRepository
from app.repositories.membership import MembershipRepository
from app.repositories.navigation import NavigationRepository
from app.repositories.notification import NotificationRepository
from app.repositories.page import PageRepository
from app.repositories.refund import RefundRepository
from app.schemas.marketing import CouponCreate
from app.schemas.navigation import NavigationItemCreate, NavigationItemUpdate
from app.schemas.page import PageConversionEventInput, PageVariantInput
from app.schemas.users import AddressCreate, AddressUpdate
from app.services.cart import CartError, CartLine, CartService
from app.services.freight import FreightError, FreightLine, FreightService
from app.services.marketing import CouponError, MarketingService
from app.services.membership import MembershipError, MembershipService
from app.services.navigation import NavigationError, NavigationService
from app.services.notification import NotificationError, NotificationService
from app.services.page import PageSchemaError, PageService
from app.services.refund import RefundError, RefundService
from app.services.user_profile import UserProfileService


def test_cart_memory_limits_and_lifecycle() -> None:
    """内存购物车应覆盖数量上限、更新、删除和清理分支。"""
    service = CartService()
    service.max_total_quantity = 3

    async def run() -> None:
        with pytest.raises(CartError, match="数量必须大于零"):
            await service.add("user", CartLine(1, 0, 100), use_database=False)
        assert await service.add("user", CartLine(1, 2, 100), use_database=False) == CartLine(1, 2, 100)
        with pytest.raises(CartError, match="购物车数量已达到上限"):
            await service.add("user", CartLine(2, 2, 200), use_database=False)
        assert await service.update("user", CartLine(1, 3, 100), use_database=False) == CartLine(1, 3, 100)
        with pytest.raises(CartError, match="购物车项不存在"):
            await service.update("user", CartLine(9, 1, 100), use_database=False)
        await service.remove("user", 1, use_database=False)
        await service.clear_items("user", [1, 2], use_database=False)
        assert await service.list("user", use_database=False) == []

    asyncio.run(run())


def test_freight_calculation_modes_and_template_errors() -> None:
    """运费服务覆盖重量、件数、平邮、包邮和模板错误分支。"""
    fallback = cast(
        FreightTemplateItem,
        SimpleNamespace(
            region_codes=[],
            first_unit=Decimal("1"),
            first_fee=100,
            additional_unit=Decimal("1"),
            additional_fee=50,
            free_condition={"min_amount": 1000},
        ),
    )
    weight_template = cast(FreightTemplate, SimpleNamespace(enabled=True, type="WEIGHT", items=[fallback]))
    lines = [FreightLine(quantity=2, weight_grams=1000, price_cents=400)]
    assert FreightService.calculate_amount(weight_template, fallback, lines, 800) == 150
    assert FreightService.calculate_amount(weight_template, fallback, lines, 1000) == 0

    piece_item = cast(
        FreightTemplateItem,
        SimpleNamespace(
            region_codes=["110000"],
            first_unit=Decimal("1"),
            first_fee=80,
            additional_unit=Decimal("2"),
            additional_fee=30,
            free_condition={},
        ),
    )
    piece_template = cast(FreightTemplate, SimpleNamespace(enabled=True, type="PIECE", items=[piece_item, fallback]))
    assert FreightService.calculate_amount(piece_template, piece_item, lines, 800) == 110
    flat_template = cast(FreightTemplate, SimpleNamespace(enabled=True, type="FLAT", items=[fallback]))
    assert FreightService.calculate_amount(flat_template, fallback, lines, 800) == 100
    assert FreightService.calculate_amount(None, None, lines, 800) == 0

    repository = AsyncMock(spec=FreightRepository)
    repository.get_template.return_value = cast(FreightTemplate, SimpleNamespace(enabled=False, items=[]))
    service = FreightService(repository=repository)

    async def run() -> None:
        with pytest.raises(FreightError, match="不存在或未启用"):
            await service.calculate_lines(cast(AsyncSession, object()), lines, "110000", 800, template_id=7)

    asyncio.run(run())


def test_user_profile_address_service_delegates_and_reassigns_default() -> None:
    """地址服务覆盖创建首地址、取消默认和删除后补默认。"""
    now = datetime.now(UTC)
    user = cast(
        User,
        SimpleNamespace(
            id=7,
            phone="13800000000",
            nickname="用户",
            avatar="",
            gender="UNKNOWN",
            status="ACTIVE",
            birthday=None,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        ),
    )
    first = cast(
        Address,
        SimpleNamespace(
            id=1,
            user_id=7,
            receiver_name="甲",
            phone="13800000000",
            province_code="110000",
            city_code="110100",
            district_code="110101",
            detail="地址甲",
            is_default=True,
            created_at=now,
            updated_at=now,
        ),
    )
    second = cast(Address, SimpleNamespace(**{**vars(first), "id": 2, "receiver_name": "乙", "is_default": False}))
    repository = AsyncMock()
    repository.get.return_value = user
    repository.list_addresses.side_effect = [[first], [second]]
    repository.add_address.return_value = second
    repository.get_address_for_update.side_effect = [second, first]
    service = UserProfileService(repository)
    payload = AddressCreate.model_validate(
        {
            "receiverName": "乙",
            "phone": "13800000000",
            "provinceCode": "110000",
            "cityCode": "110100",
            "districtCode": "110101",
            "detail": "地址乙",
        }
    )

    async def run() -> None:
        assert (await service.get_profile(cast(AsyncSession, object()), 7))["id"] == 7
        created = await service.create_address(cast(AsyncSession, object()), 7, payload)
        assert created["id"] == 2
        updated = await service.update_address(
            cast(AsyncSession, object()), 7, 2, AddressUpdate.model_validate({"isDefault": False})
        )
        assert updated["id"] == 2
        await service.delete_address(cast(AsyncSession, object()), 7, 1)
        assert second.is_default is True

    asyncio.run(run())


def test_membership_notification_and_navigation_services() -> None:
    """会员、通知和导航服务覆盖正常响应与错误分支。"""
    now = datetime.now(UTC)
    user = cast(
        User,
        SimpleNamespace(
            id=1,
            phone="13800000000",
            nickname="会员",
            avatar="",
            member_level="NORMAL",
            points=20,
            tags=["老客"],
            created_at=now,
            addresses=[],
        ),
    )
    membership_repository = AsyncMock(spec=MembershipRepository)
    membership_repository.list_users.return_value = [user]
    membership_repository.count_users.return_value = 1
    membership_repository.count_orders.return_value = 2
    membership_repository.sum_paid_orders.return_value = 3000
    membership_repository.get_with_addresses.return_value = user
    membership_repository.list_orders.return_value = []
    membership_repository.get_for_update.return_value = user
    membership = MembershipService(membership_repository)

    notification = SimpleNamespace(
        id=3,
        notification_type="ORDER",
        title="订单更新",
        content="已发货",
        read_at=None,
        created_at=now,
    )
    notification_repository = AsyncMock(spec=NotificationRepository)
    notification_repository.list_for_user.return_value = [notification]
    notification_repository.unread_count.return_value = 1
    notification_repository.get_for_user.return_value = notification
    notification_repository.mark_all_read.return_value = 1
    notifications = NotificationService(notification_repository)

    navigation = SimpleNamespace(
        id=4,
        label="产品",
        href="/products",
        location="header",
        kind="internal",
        open_new_tab=False,
        sort_order=1,
        enabled=True,
    )
    navigation_repository = AsyncMock(spec=NavigationRepository)
    navigation_repository.list_enabled.return_value = [navigation]
    navigation_repository.list_all.return_value = [navigation]
    navigation_repository.create.return_value = navigation
    navigation_repository.get_for_update.return_value = navigation
    navigation_repository.delete.return_value = True
    navigations = NavigationService(navigation_repository)

    async def run() -> None:
        session = cast(AsyncSession, object())
        members_response = await membership.list_members(session, 1, 20)
        members_meta = cast(dict[str, object], members_response["meta"])
        assert members_meta["total"] == 1
        assert (await membership.get_member(session, 1))["phone"] == "138****0000"
        assert (await membership.update_tags(session, 1, [" 新客", "新客", " "]))["tags"] == ["新客"]
        with pytest.raises(MembershipError):
            await membership.update_level(session, 1, "VIP")
        assert (await membership.update_level(session, 1, "MEMBER"))["memberLevel"] == "MEMBER"

        assert (await notifications.list_for_user(session, 1))["unreadCount"] == 1
        assert (await notifications.mark_read(session, 1, 3))["id"] == 3
        assert (await notifications.mark_all_read(session, 1))["updated"] == 1
        notification_repository.get_for_user.return_value = None
        with pytest.raises(NotificationError):
            await notifications.mark_read(session, 1, 404)

        payload = NavigationItemCreate(label="产品", href="/products")
        assert (await navigations.list_enabled(session, "header"))[0]["id"] == 4
        assert (await navigations.list_admin(session))[0]["id"] == 4
        assert (await navigations.create(session, payload))["id"] == 4
        assert (await navigations.update(session, 4, NavigationItemUpdate(label="商品", href="/products")))[
            "label"
        ] == "商品"
        assert (await navigations.remove(session, 4))["deleted"] is True
        navigation_repository.get_for_update.return_value = None
        with pytest.raises(NavigationError):
            await navigations.update(session, 4, NavigationItemUpdate(label="商品", href="/products"))

    asyncio.run(run())


def test_marketing_page_and_refund_service_branches() -> None:
    """营销、页面 Schema 和退款服务覆盖重复、校验和失败重试路径。"""
    now = datetime.now(UTC)
    coupon = SimpleNamespace(
        id=1,
        code="WELCOME",
        name="新人券",
        coupon_type="FULL_REDUCTION",
        threshold_cents=1000,
        discount_cents=100,
        discount_percent=None,
        total_count=10,
        claimed_count=0,
        used_count=0,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        enabled=True,
    )
    marketing_repository = AsyncMock()
    marketing_repository.list_coupons.return_value = [coupon]
    marketing_repository.get_coupon.return_value = None
    marketing_repository.get_claim.return_value = None
    marketing = MarketingService(marketing_repository)

    page = cast(
        StorePage,
        SimpleNamespace(
            id=1,
            slug="home",
            channel="site",
            name="首页",
            status="PUBLISHED",
            version=1,
            schema={"title": "首页", "components": []},
            is_home=False,
            published_at=None,
            created_at=now,
            updated_at=now,
        ),
    )
    page_repository = AsyncMock(spec=PageRepository)
    page_repository.get.return_value = page
    page_repository.get_by_slug.return_value = page
    page_repository.list_pages.return_value = [page]
    page_repository.list_published_pages.return_value = [page]
    page_repository.list_variants.return_value = []
    page_repository.get_variant.return_value = None
    page_service = PageService(page_repository)
    refund = SimpleNamespace(
        id=1,
        refund_no="RF-1",
        payment_id=2,
        amount_cents=100,
        status="PENDING",
        attempt_count=0,
        fail_reason=None,
        refunded_at=None,
        updated_at=now,
        transaction_id=None,
        provider_response={},
    )
    payment = SimpleNamespace(
        id=2,
        user_id=7,
        order_id=3,
        status="SUCCESS",
        amount_cents=100,
        transaction_id="trade-1",
        order=SimpleNamespace(
            items=[SimpleNamespace(sku_id=9, quantity=1)],
            refund_status="NONE",
        ),
    )

    class FakeRefundGateway:
        """可控的退款渠道替身。"""

        def __init__(self) -> None:
            self.should_fail = False

        async def refund(self, *, transaction_id: str, refund_no: str, amount_cents: int) -> str:
            """按测试开关返回成功或抛出渠道异常。"""
            if self.should_fail:
                raise RuntimeError("渠道暂不可用")
            return "refund-trade-1"

    gateway = FakeRefundGateway()
    refund_service = RefundService(gateway=gateway)
    refund_service.refunds = AsyncMock(spec=RefundRepository)
    refund_service.payments = AsyncMock()
    refund_service.orders = AsyncMock()
    refund_service.inventory = AsyncMock()
    refund_service.refunds.get_for_update.return_value = refund
    refund_service.refunds.sum_active_amount.return_value = 0
    refund_service.payments.get_by_id.return_value = payment

    async def run() -> None:
        session = cast(AsyncSession, object())
        assert (await marketing.list_coupons(session))[0]["code"] == "WELCOME"
        created = await marketing.create_coupon(
            session,
            CouponCreate.model_validate(
                {
                    "code": "WELCOME",
                    "name": "新人券",
                    "couponType": "FULL_REDUCTION",
                    "thresholdCents": 1000,
                    "discountCents": 100,
                    "startsAt": (now - timedelta(days=1)).isoformat(),
                    "endsAt": (now + timedelta(days=1)).isoformat(),
                }
            ),
        )
        assert created["code"] == "WELCOME"
        marketing_repository.get_coupon.return_value = coupon
        assert (await marketing.claim(session, 7, "WELCOME"))["claimed"] is True
        marketing_repository.get_claim.return_value = SimpleNamespace(id=1)
        assert (await marketing.claim(session, 7, "WELCOME"))["duplicate"] is True
        marketing_repository.get_coupon.return_value = None
        with pytest.raises(CouponError):
            await marketing.claim(session, 7, "MISSING")

        assert (await page_service.get(session, 1))["slug"] == "home"
        assert (await page_service.get_by_slug(session, "home"))["channel"] == "site"
        assert await page_service.list_pages(session)
        assert await page_service.list_public_pages(session)
        page_repository.get.return_value = None
        with pytest.raises(PageSchemaError):
            await page_service.get(session, 404)
        page_repository.get.return_value = page
        page_repository.get_variant.return_value = cast(
            PageVariant,
            SimpleNamespace(id=5, page_id=1, key="a", name="A", allocation_percent=100, schema={}, enabled=True),
        )
        assert (
            await page_service.save_variant(
                session,
                1,
                PageVariantInput.model_validate(
                    {"key": "a", "name": "A", "schema": {"slug": "a", "version": 1, "components": []}}
                ),
            )
        )["key"] == "a"
        assert (
            await page_service.record_event(session, 1, PageConversionEventInput.model_validate({"eventName": "view"}))
        )["accepted"] is True
        page.channel = "site"
        assert (await page_service.publish(session, 1))["status"] == "PUBLISHED"

        processed = await refund_service.process(session, 1)
        assert processed.status == "SUCCESS"
        assert processed.transaction_id == "refund-trade-1"
        gateway.should_fail = True
        refund.status = "FAILED"
        with pytest.raises(RefundError, match="稍后重试"):
            await refund_service.process(session, 1)

    asyncio.run(run())
