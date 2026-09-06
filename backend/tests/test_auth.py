"""认证和健康检查接口测试。"""

from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.main import app

client = TestClient(app)


def test_health() -> None:
    """健康检查返回成功。"""
    response = client.get("/health")
    assert response.status_code == 200


def test_readiness_reports_dependency_results(monkeypatch: MonkeyPatch) -> None:
    """就绪检查按三个依赖的真实结果决定状态。"""

    async def all_ready() -> dict[str, bool]:
        return {"database": True, "redis": True, "objectStorage": True}

    monkeypatch.setattr("app.api.health.readiness_checks", all_ready)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["checks"] == {
        "database": True,
        "redis": True,
        "objectStorage": True,
    }


def test_sms_rate_limit() -> None:
    """同一手机号六十秒内只能发送一次验证码。"""
    assert client.post("/api/v1/auth/sms/send", json={"phone": "13800000000"}).status_code == 200
    assert client.post("/api/v1/auth/sms/send", json={"phone": "13800000000"}).status_code == 429


def test_login_token() -> None:
    """登录签发 access token 和 HttpOnly refresh Cookie。"""
    response = client.post("/api/v1/auth/login", json={"phone": "13800000000", "code": "123456"})
    assert response.status_code == 200
    assert response.json()["data"]["accessToken"].count(".") == 2
    assert response.cookies.get("refresh_token") is not None


def test_refresh_and_logout() -> None:
    """刷新令牌能够轮换，退出登录会删除 Cookie。"""
    login_response = client.post(
        "/api/v1/auth/login",
        json={"phone": "13900000000", "code": "123456"},
    )
    access_token = login_response.json()["data"]["accessToken"]
    origin_headers = {"Origin": "http://localhost:5173"}
    refresh_response = client.post("/api/v1/auth/refresh", headers=origin_headers)
    assert refresh_response.status_code == 200
    assert refresh_response.json()["data"]["accessToken"].count(".") == 2
    logout_response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {access_token}", **origin_headers},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["data"] == {"loggedOut": True}


def test_protected_user_api_rejects_missing_token() -> None:
    """用户资料接口必须校验 access token。"""
    response = client.get("/api/v1/user/me")
    assert response.status_code == 401
    assert response.json()["code"] == 40101
