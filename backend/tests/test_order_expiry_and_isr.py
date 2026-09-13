"""订单超时任务与官网 ISR 通知边界测试。"""

import asyncio
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import settings
from app.services import isr
from app.tasks import order_expiry


class _WorkflowStub:
    """提供订单超时任务所需的最小工作流替身。"""

    def __init__(self, orders: Sequence[object], *, error: Exception | None = None) -> None:
        self.orders = SimpleNamespace(list_expired_for_update=AsyncMock(return_value=orders))
        self.expire_order = AsyncMock(side_effect=error)


def test_expire_pending_orders_returns_zero_without_expired_orders(monkeypatch: pytest.MonkeyPatch) -> None:
    """没有到期订单时不执行取消动作并返回零。"""
    workflow = _WorkflowStub([])

    @asynccontextmanager
    async def fake_transaction() -> AsyncIterator[object]:
        yield object()

    monkeypatch.setattr(order_expiry, "OrderWorkflow", lambda: workflow)
    monkeypatch.setattr(order_expiry, "transaction", fake_transaction)

    assert asyncio.run(order_expiry.expire_pending_orders()) == 0
    workflow.orders.list_expired_for_update.assert_awaited_once()
    workflow.expire_order.assert_not_awaited()


def test_expire_pending_orders_processes_batch_and_forwards_batch_size(monkeypatch: pytest.MonkeyPatch) -> None:
    """任务逐个取消到期订单，并将批量大小传给仓储查询。"""
    orders = [SimpleNamespace(id=11), SimpleNamespace(id=12)]
    workflow = _WorkflowStub(orders)

    @asynccontextmanager
    async def fake_transaction() -> AsyncIterator[str]:
        yield "session"

    monkeypatch.setattr(order_expiry, "OrderWorkflow", lambda: workflow)
    monkeypatch.setattr(order_expiry, "transaction", fake_transaction)

    assert asyncio.run(order_expiry.expire_pending_orders(batch_size=2)) == 2
    workflow.orders.list_expired_for_update.assert_awaited_once()
    session, expires_at, batch_size = workflow.orders.list_expired_for_update.await_args.args
    assert session == "session"
    assert isinstance(expires_at, datetime) and expires_at.tzinfo == UTC
    assert batch_size == 2
    assert [call.args for call in workflow.expire_order.await_args_list] == [
        ("session", orders[0], "expiry:11"),
        ("session", orders[1], "expiry:12"),
    ]


def test_expire_pending_orders_propagates_workflow_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """单笔取消失败时异常向上传播，事务上下文负责回滚。"""
    workflow = _WorkflowStub([SimpleNamespace(id=3)], error=RuntimeError("写入失败"))

    @asynccontextmanager
    async def fake_transaction() -> AsyncIterator[object]:
        yield object()

    monkeypatch.setattr(order_expiry, "OrderWorkflow", lambda: workflow)
    monkeypatch.setattr(order_expiry, "transaction", fake_transaction)

    with pytest.raises(RuntimeError, match="写入失败"):
        asyncio.run(order_expiry.expire_pending_orders())


def test_isr_revalidate_returns_false_without_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置官网地址或令牌时跳过网络请求。"""
    configured = replace(settings, nextjs_base_url="", revalidate_token="")
    monkeypatch.setattr(isr, "settings", configured)
    assert asyncio.run(isr.trigger_isr_revalidate("home")) is False


def test_isr_revalidate_handles_success_http_error_and_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """ISR 通知覆盖成功、HTTP 错误和网络异常三种结果。"""
    configured = replace(settings, nextjs_base_url="https://site.example", revalidate_token="token")
    monkeypatch.setattr(isr, "settings", configured)

    class _Response:
        def __init__(self, status_code: int) -> None:
            self.status_code = status_code

    client = AsyncMock()
    client.__aenter__.return_value = client
    client.post.side_effect = [_Response(200), _Response(500), httpx.ConnectError("断网")]
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_: client)

    assert asyncio.run(isr.trigger_isr_revalidate("home", tags=("site-pages",))) is True
    assert asyncio.run(isr.trigger_isr_revalidate("home")) is False
    assert asyncio.run(isr.trigger_isr_revalidate("home")) is False
    assert client.post.await_count == 3
    first_call = client.post.await_args_list[0]
    assert first_call.kwargs["json"] == {"slug": "home", "tags": ["site-pages"]}
    assert first_call.kwargs["headers"]["x-revalidate-token"] == "token"
