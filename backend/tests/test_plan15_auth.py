"""plan-15 认证安全回归测试。"""

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.network import get_client_ip
from app.main import app
from app.services.auth import AuthenticationError, AuthService


def test_refresh_token_replay_is_rejected_after_rotation() -> None:
    """refresh 成功轮换后，旧令牌不能再次使用。"""
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"phone": "15100000001", "code": "123456"})
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


def test_logout_revokes_refresh_token() -> None:
    """退出登录后，Cookie 中的 refresh token 立即撤销。"""
    client = TestClient(app)
    login = client.post("/api/v1/auth/login", json={"phone": "15100000002", "code": "123456"})
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
