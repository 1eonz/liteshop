"""一期新增设置、页面 Schema 和订单列表接口测试。"""

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_theme_and_page_schema_contracts() -> None:
    """主题接口和低代码页面 Schema 返回稳定版本字段。"""
    theme = client.get("/api/v1/settings/theme")
    assert theme.status_code == 200
    assert theme.json()["data"]["primaryColor"] == "#ff6b6b"
    page = client.get("/api/v1/pages/1/schema")
    assert page.status_code == 200
    assert page.json()["data"]["version"] == 1
    assert page.json()["data"]["components"]


def test_theme_update_is_idempotent() -> None:
    """主题更新使用请求 ID 幂等，重复请求返回同一快照。"""
    token = create_access_token("settings-user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "theme-update-1"}
    payload = {"primaryColor": "#1890ff", "navigationStyle": "solid", "tabbarStyle": "minimal"}
    first = client.put("/api/v1/settings/theme", headers=headers, json=payload)
    second = client.put("/api/v1/settings/theme", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"] == second.json()["data"]
    reset_headers = {**headers, "X-Request-Id": "theme-update-reset"}
    client.put(
        "/api/v1/settings/theme",
        headers=reset_headers,
        json={"primaryColor": "#ff6b6b", "navigationStyle": "glass", "tabbarStyle": "gallery"},
    )


def test_memory_order_list_reports_total() -> None:
    """无数据库开发模式的订单列表也返回完整分页契约。"""
    token = create_access_token("orders-list-user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "orders-list-create"}
    created = client.post(
        "/api/v1/orders",
        headers=headers,
        json={"items": [{"skuId": 1, "quantity": 1, "priceCents": 100}], "addressSnapshot": {}, "totalAmount": 100},
    )
    assert created.status_code == 200
    listed = client.get("/api/v1/orders", headers={"Authorization": f"Bearer {token}"})
    assert listed.status_code == 200
    assert listed.json()["data"]["meta"]["total"] == 1
    assert listed.json()["data"]["items"][0]["status"] == "PENDING_PAYMENT"
