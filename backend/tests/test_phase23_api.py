"""二期、三期新增接口的契约和边界测试。"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import cast
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.repositories.navigation import NavigationRepository
from app.schemas.contact import ContactFormStatusUpdate
from app.schemas.logistics import TrackingEventCreate
from app.schemas.marketing import CouponCreate
from app.schemas.page import PageSchemaInput
from app.services.navigation import NavigationService
from app.services.page import PageSchemaError, PageService

client = TestClient(app)


def test_public_page_endpoint_returns_home_fallback() -> None:
    """开发模式官网页面接口返回可渲染的首页 Schema。"""
    response = client.get("/api/v1/site/pages/home")
    assert response.status_code == 200
    assert response.json()["data"]["slug"] == "home"
    assert response.json()["data"]["components"]


def test_public_page_endpoint_rejects_unsafe_slug() -> None:
    """官网页面路由不允许路径穿越或脚本片段。"""
    response = client.get("/api/v1/site/pages/%2E%2E")
    assert response.status_code == 404


def test_navigation_service_forwards_location_filter() -> None:
    """服务层必须把 header/footer 过滤条件传给仓储层。"""
    repository = AsyncMock(spec=NavigationRepository)
    repository.list_enabled.return_value = []
    service = NavigationService(repository)
    session = cast(AsyncSession, object())
    asyncio.run(service.list_enabled(session, "footer"))
    repository.list_enabled.assert_awaited_once_with(session, "footer")


def test_page_schema_rejects_script_and_hardcoded_style() -> None:
    """页面 Schema 只允许安全内容和 Design Token 样式。"""
    script_schema = PageSchemaInput.model_validate(
        {
            "slug": "unsafe",
            "version": 1,
            "components": [{"id": "x", "type": "RichText", "props": {"text": "<script>alert(1)</script>"}}],
        }
    )
    with pytest.raises(PageSchemaError):
        PageService.validate(script_schema)
    style_schema = PageSchemaInput.model_validate(
        {
            "slug": "hardcoded-style",
            "version": 1,
            "components": [{"id": "x", "type": "Spacer", "style": {"padding": "8px"}}],
        }
    )
    with pytest.raises(PageSchemaError):
        PageService.validate(style_schema)


def test_coupon_and_tracking_dtos_validate_aliases_and_window() -> None:
    """优惠券时间窗和物流字段别名保持契约一致。"""
    starts_at = datetime.now(UTC)
    coupon = CouponCreate(
        code="WELCOME10",
        name="新人券",
        couponType="FULL_REDUCTION",
        thresholdCents=9900,
        discountCents=1000,
        startsAt=starts_at,
        endsAt=starts_at + timedelta(days=1),
    )
    assert coupon.threshold_cents == 9900
    tracking = TrackingEventCreate(
        status="IN_TRANSIT",
        description="已揽收",
        occurredAt=starts_at,
    )
    assert tracking.occurred_at == starts_at
    with pytest.raises(ValueError):
        ContactFormStatusUpdate(status="INVALID")
