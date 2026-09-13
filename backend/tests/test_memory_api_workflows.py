"""开发沙箱公开 API 和用户交互流程测试。"""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def _headers(subject: str, request_id: str | None = None) -> dict[str, str]:
    """构造带 access token 和可选幂等请求 ID 的请求头。"""
    headers = {"Authorization": f"Bearer {create_access_token(subject)}"}
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


def _address_payload(name: str, is_default: bool = False) -> dict[str, object]:
    """构造符合地址契约的测试数据。"""
    return {
        "receiverName": name,
        "phone": "13800000000",
        "provinceCode": "110000",
        "cityCode": "110100",
        "districtCode": "110101",
        "detail": f"{name}的集成测试地址",
        "isDefault": is_default,
    }


def test_memory_user_profile_and_address_default_switching() -> None:
    """开发模式地址增改删应维护唯一默认地址。"""
    subject = f"memory-address-{uuid4().hex}"
    headers = _headers(subject)

    profile = client.get("/api/v1/user/me", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["id"] == subject
    assert client.get("/api/v1/user/addresses", headers=headers).json()["data"]["items"] == []

    first = client.post(
        "/api/v1/user/addresses",
        headers=_headers(subject, f"address-create-{uuid4().hex}"),
        json=_address_payload("第一联系人"),
    )
    assert first.status_code == 200
    first_id = first.json()["data"]["id"]
    assert first.json()["data"]["isDefault"] is True

    second = client.post(
        "/api/v1/user/addresses",
        headers=_headers(subject, f"address-create-{uuid4().hex}"),
        json=_address_payload("第二联系人", is_default=True),
    )
    assert second.status_code == 200
    second_id = second.json()["data"]["id"]
    addresses = client.get("/api/v1/user/addresses", headers=headers).json()["data"]["items"]
    assert [item["isDefault"] for item in addresses] == [False, True]

    unset_default = client.put(
        f"/api/v1/user/addresses/{second_id}",
        headers=_headers(subject, f"address-update-{uuid4().hex}"),
        json={"isDefault": False, "detail": "更新后的地址"},
    )
    assert unset_default.status_code == 200
    assert unset_default.json()["data"]["isDefault"] is False
    addresses = client.get("/api/v1/user/addresses", headers=headers).json()["data"]["items"]
    assert next(item for item in addresses if item["id"] == first_id)["isDefault"] is True

    deleted = client.delete(
        f"/api/v1/user/addresses/{first_id}",
        headers=_headers(subject, f"address-delete-{uuid4().hex}"),
    )
    assert deleted.status_code == 200
    missing = client.delete(
        f"/api/v1/user/addresses/{first_id}",
        headers=_headers(subject, f"address-delete-missing-{uuid4().hex}"),
    )
    assert missing.status_code == 404


def test_memory_catalog_page_and_settings_public_contracts() -> None:
    """开发模式公开商品、页面、主题和配置接口保持稳定字段。"""
    products = client.get("/api/v1/products?page=1&pageSize=2")
    assert products.status_code == 200
    assert products.json()["data"]["meta"] == {"page": 1, "pageSize": 2, "total": 3, "hasNext": True}
    assert client.get("/api/v1/products/search?q=卫衣").json()["data"]["items"][0]["id"] == 2
    assert client.get("/api/v1/products/search?q=不存在").json()["data"]["items"] == []
    assert client.get("/api/v1/categories").json()["data"]["items"] == []
    assert client.get("/api/v1/products/1").json()["data"]["skus"]
    assert client.get("/api/v1/products/999").status_code == 404

    public_pages = client.get("/api/v1/site/pages")
    assert public_pages.status_code == 200
    assert public_pages.json()["data"]["items"][0]["slug"] == "home"
    assert client.get("/api/v1/site/pages/home").json()["data"]["channel"] == "site"
    assert client.get("/api/v1/site/pages/about").status_code == 404
    assert client.get("/api/v1/site/pages/%2E%2E").status_code == 404
    assert client.get("/api/v1/pages/1/schema").json()["data"]["version"] == 1
    assert client.get("/api/v1/pages/999/schema").json()["data"]["components"] == []

    assert client.get("/api/v1/settings/theme").json()["data"]["primaryColor"] == "#ff6b6b"
    assert client.get("/api/v1/settings/site").json()["data"]["siteName"] == "LiteShop"
    assert len(client.get("/api/v1/settings/shipping-companies").json()["data"]["items"]) == 4
    assert {item["key"] for item in client.get("/api/v1/settings/feature-flags").json()["data"]["items"]} == {
        "h5Favorites",
        "h5PaymentSandbox",
        "adminDashboard",
    }


def test_memory_theme_site_and_navigation_updates_are_idempotent() -> None:
    """开发模式主题、官网设置和导航公开读取使用幂等请求。"""
    subject = f"memory-settings-{uuid4().hex}"
    theme_headers = _headers(subject, f"theme-{uuid4().hex}")
    theme_payload = {"primaryColor": "#1890ff", "navigationStyle": "solid", "tabbarStyle": "minimal"}
    first_theme = client.put("/api/v1/settings/theme", headers=theme_headers, json=theme_payload)
    second_theme = client.put("/api/v1/settings/theme", headers=theme_headers, json=theme_payload)
    assert first_theme.status_code == second_theme.status_code == 200
    assert first_theme.json()["data"] == second_theme.json()["data"]

    site_headers = _headers(subject, f"site-{uuid4().hex}")
    site_payload = {"siteName": "LiteShop 测试站", "logoUrl": "", "contactEmail": "team@example.com"}
    site = client.put("/api/v1/settings/site", headers=site_headers, json=site_payload)
    assert site.status_code == 200
    assert site.json()["data"]["siteName"] == "LiteShop 测试站"

    navigation = client.get("/api/v1/site/navigation?location=header")
    assert navigation.status_code == 200
    assert len(navigation.json()["data"]["items"]) == 3
    assert client.get("/api/v1/site/navigation?location=footer").json()["data"]["items"] == []


def test_memory_cart_notifications_and_logistics_contracts() -> None:
    """购物车、通知和物流接口在开发模式提供可用的最小行为。"""
    subject = f"memory-cart-{uuid4().hex}"
    token_headers = _headers(subject)
    add_headers = _headers(subject, f"cart-add-{uuid4().hex}")
    payload = {"skuId": 1, "quantity": 2, "priceCents": 12900}
    added = client.post("/api/v1/cart/items", headers=add_headers, json=payload)
    assert added.status_code == 200
    assert added.json()["data"]["item"]["quantity"] == 2

    updated = client.put(
        "/api/v1/cart/items/1",
        headers=_headers(subject, f"cart-update-{uuid4().hex}"),
        json={"skuId": 1, "quantity": 3, "priceCents": 12900},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["item"]["quantity"] == 3
    mismatch = client.put(
        "/api/v1/cart/items/2",
        headers=_headers(subject, f"cart-mismatch-{uuid4().hex}"),
        json={"skuId": 1, "quantity": 1, "priceCents": 12900},
    )
    assert mismatch.status_code == 422
    removed = client.delete(
        "/api/v1/cart/items/1",
        headers=_headers(subject, f"cart-remove-{uuid4().hex}"),
    )
    assert removed.status_code == 200
    assert client.get("/api/v1/cart", headers=token_headers).json()["data"]["items"] == []

    notifications = client.get("/api/v1/notifications", headers=token_headers)
    assert notifications.json()["data"] == {"items": [], "unreadCount": 0}
    assert (
        client.put(
            "/api/v1/notifications/5/read",
            headers=_headers(subject, f"notification-read-{uuid4().hex}"),
        ).json()["data"]["id"]
        == 5
    )
    assert client.put(
        "/api/v1/notifications/read-all",
        headers=_headers(subject, f"notification-read-all-{uuid4().hex}"),
    ).json()["data"] == {"updated": 0}

    assert client.get("/api/v1/orders/5/tracking", headers=token_headers).json()["data"]["items"] == []
    tracking = client.post(
        "/api/v1/orders/5/tracking",
        headers=_headers(subject, f"tracking-{uuid4().hex}"),
        json={"status": "IN_TRANSIT", "description": "已揽收", "occurredAt": "2026-09-12T00:00:00Z"},
    )
    assert tracking.status_code == 503


def test_memory_contact_favorites_after_sales_and_reviews_errors() -> None:
    """未启用数据库时，写入型扩展接口返回明确的服务状态。"""
    contact_payload = {
        "name": "测试访客",
        "email": "visitor@example.com",
        "phone": "13800000000",
        "company": "LiteShop",
        "message": "希望了解合作方案",
    }
    request_id = f"contact-{uuid4().hex}"
    first = client.post("/api/v1/contact/forms", headers={"X-Request-Id": request_id}, json=contact_payload)
    second = client.post("/api/v1/contact/forms", headers={"X-Request-Id": request_id}, json=contact_payload)
    assert first.status_code == second.status_code == 202
    assert first.json()["data"] == second.json()["data"]
    invalid = client.post(
        "/api/v1/contact/forms",
        headers={"X-Request-Id": f"contact-invalid-{uuid4().hex}"},
        json={**contact_payload, "website": "https://spam.example"},
    )
    assert invalid.status_code == 422

    subject = f"memory-extension-{uuid4().hex}"
    headers = _headers(subject)
    assert client.get("/api/v1/favorites", headers=headers).json()["data"]["items"] == []
    assert (
        client.put(
            "/api/v1/favorites/1",
            headers=_headers(subject, f"favorite-{uuid4().hex}"),
        ).status_code
        == 503
    )
    assert client.get("/api/v1/reviews/products/1").json()["data"] == {"averageRating": 0, "items": []}
    assert (
        client.post(
            "/api/v1/reviews",
            headers=_headers(subject, f"review-{uuid4().hex}"),
            json={"orderItemId": 1, "rating": 5, "content": "很好"},
        ).status_code
        == 503
    )
    assert client.get("/api/v1/after-sales", headers=headers).status_code == 503
    assert (
        client.post(
            "/api/v1/after-sales",
            headers=_headers(subject, f"after-sale-{uuid4().hex}"),
            json={"orderItemId": 1, "type": "REFUND_ONLY", "amountCents": 100, "reason": "不需要了"},
        ).status_code
        == 503
    )
