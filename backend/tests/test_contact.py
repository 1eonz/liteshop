"""官网联系表单 API 测试。"""

from fastapi.testclient import TestClient

from app.main import app


def test_contact_form_is_idempotent() -> None:
    """相同请求 ID 不应创建两条联系表单。"""
    client = TestClient(app)
    payload = {"name": "李明", "email": "li@example.com", "message": "希望了解演示"}
    first = client.post("/api/v1/contact/forms", headers={"X-Request-Id": "contact-test-1"}, json=payload)
    second = client.post("/api/v1/contact/forms", headers={"X-Request-Id": "contact-test-1"}, json=payload)
    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["data"] == second.json()["data"]


def test_contact_form_rejects_honeypot() -> None:
    """隐藏蜜罐字段有值时拒绝疑似机器人请求。"""
    client = TestClient(app)
    response = client.post(
        "/api/v1/contact/forms",
        headers={"X-Request-Id": "contact-test-2"},
        json={"name": "机器人", "email": "bot@example.com", "message": "spam", "website": "https://spam.local"},
    )
    assert response.status_code == 422
