"""plan-15 认证安全回归测试。"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.network import get_client_ip
from app.main import app
from app.services.admin import AdminPermissionDenied, AdminService
from app.services.auth import AuthenticationError, AuthService, auth_service


def test_refresh_token_replay_is_rejected_after_rotation(monkeypatch: pytest.MonkeyPatch) -> None:
    """refresh 成功轮换后，旧令牌不能再次使用。"""
    client = TestClient(app)
    phone = "15100000001"
    monkeypatch.setattr(auth_service, "code_generator", lambda: "518204")
    send = client.post("/api/v1/auth/sms-code", json={"phone": phone})
    assert send.status_code == 200
    login = client.post("/api/v1/auth/login", json={"phone": phone, "code": "518204"})
    old_refresh = login.cookies.get("refresh_token")
    assert old_refresh
    headers = {"Origin": "http://localhost:5173"}

    first = client.post("/api/v1/auth/refresh", headers=headers)
    assert first.status_code == 200

    # 新建客户端避免自动携带已轮换后的 Cookie，显式重放旧令牌。
    replay_client = TestClient(app)
    replay = replay_client.post(
        "/api/v1/auth/refresh",
        headers={**headers, "Authorization": f"Bearer {old_refresh}"},
    )
    assert replay.status_code == 401
    assert replay.json()["code"] == 40101


def test_logout_revokes_refresh_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """退出登录后，Cookie 中的 refresh token 立即撤销。"""
    client = TestClient(app)
    phone = "15100000002"
    monkeypatch.setattr(auth_service, "code_generator", lambda: "935172")
    send = client.post("/api/v1/auth/sms-code", json={"phone": phone})
    assert send.status_code == 200
    login = client.post("/api/v1/auth/login", json={"phone": phone, "code": "935172"})
    old_refresh = login.cookies.get("refresh_token")
    access_token = login.json()["data"]["accessToken"]
    assert old_refresh
    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": "http://localhost:5173", "Authorization": f"Bearer {access_token}"},
    )
    assert logout.status_code == 200

    replay_client = TestClient(app)
    replay = replay_client.post(
        "/api/v1/auth/refresh",
        headers={
            "Origin": "http://localhost:5173",
            "Authorization": f"Bearer {old_refresh}",
        },
    )
    assert replay.status_code == 401


def test_untrusted_forwarded_for_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置可信代理时，伪造 X-Forwarded-For 不得改变客户端 IP。"""
    monkeypatch.setattr(
        "app.core.network.settings",
        SimpleNamespace(trusted_proxy_networks=()),
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"203.0.113.9")],
            "client": ("192.0.2.10", 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )
    assert get_client_ip(request) == "192.0.2.10"


def test_trusted_proxy_forwarded_for_is_resolved(monkeypatch: pytest.MonkeyPatch) -> None:
    """直接连接方属于可信代理时，解析代理转发的客户端 IP。"""
    monkeypatch.setattr(
        "app.core.network.settings",
        SimpleNamespace(trusted_proxy_networks=("192.0.2.0/24",)),
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", b"203.0.113.9, 192.0.2.11")],
            "client": ("192.0.2.10", 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
        }
    )
    assert get_client_ip(request) == "203.0.113.9"


def test_sms_code_concurrent_consume_only_succeeds_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """验证码的原子消费语义保证并发请求最多一个成功。"""

    class AtomicRedis:
        def __init__(self) -> None:
            self.consumed = False

        async def eval(self, *_args: object) -> str | None:
            if self.consumed:
                return None
            self.consumed = True
            return "123456"

    redis = AtomicRedis()
    monkeypatch.setattr("app.services.auth.settings", SimpleNamespace(use_database=True))
    monkeypatch.setattr("app.services.auth.redis_client", redis)
    service = AuthService()

    async def consume() -> bool:
        try:
            await service.verify_sms_code("15100000003", "123456")
        except AuthenticationError:
            return False
        return True

    async def run_concurrently() -> list[bool]:
        return list(await asyncio.gather(consume(), consume()))

    results = asyncio.run(run_concurrently())
    assert sorted(results) == [False, True]


def test_development_sms_code_is_random_and_one_time(monkeypatch: pytest.MonkeyPatch) -> None:
    """开发控制台验证码应随机生成，成功校验后立即失效。"""

    class CapturingSmsProvider:
        def __init__(self) -> None:
            self.codes: list[str] = []

        async def send(self, _phone: str, code: str) -> None:
            self.codes.append(code)

    settings = SimpleNamespace(use_database=False, sms_provider="console")
    monkeypatch.setattr("app.services.auth.settings", settings)
    generated = iter((123456, 654321))
    provider = CapturingSmsProvider()
    service = AuthService(
        sms_provider=provider,
        code_generator=lambda: f"{next(generated):06d}",
    )

    asyncio.run(service.send_sms_code("15100000004"))
    asyncio.run(service.send_sms_code("15100000005"))
    assert provider.codes == ["123456", "654321"]
    asyncio.run(service.verify_sms_code("15100000004", "123456"))
    with pytest.raises(AuthenticationError, match="INVALID_CODE"):
        asyncio.run(service.verify_sms_code("15100000004", "123456"))


def test_production_cannot_use_console_sms_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """预发布和生产环境必须配置真实短信渠道。"""
    monkeypatch.setenv("JWT_SECRET", "j" * 32)
    monkeypatch.setenv("PAYMENT_CALLBACK_SECRET", "p" * 32)

    with pytest.raises(ValueError, match="禁止使用 console"):
        Settings(
            environment="production",
            use_database=True,
            sms_provider="console",
            jwt_secret="j" * 32,
            payment_callback_secret="p" * 32,
            payment_wechat_callback_secret="w" * 32,
            payment_alipay_callback_secret="a" * 32,
        )


def test_admin_subject_must_be_numeric() -> None:
    """管理员权限校验拒绝硬编码 admin 主体。"""
    service = AdminService()
    with pytest.raises(AdminPermissionDenied, match="无效管理员身份"):
        asyncio.run(service.require_permission(None, "admin", "settings.write"))  # type: ignore[arg-type]
