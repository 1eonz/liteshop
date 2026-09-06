"""后台操作日志测试。"""

import asyncio
from unittest.mock import AsyncMock

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.operation_log import OperationLog
from app.services.admin import AdminService


def test_operation_log_captures_actor_and_snapshots() -> None:
    """操作日志包含操作人、资源、前后值和请求上下文。"""
    session = AsyncMock(spec=AsyncSession)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(ip="127.0.0.1", user_agent="pytest")
    asyncio.run(
        AdminService.audit(
            session,
            user_id="42",
            resource_type="PRODUCT",
            resource_id=7,
            action="UPDATE",
            request_id="request-operation-log",
            before_data={"name": "旧名称"},
            after_data={"name": "新名称"},
        )
    )
    entry = session.add.call_args.args[0]
    assert isinstance(entry, OperationLog)
    assert entry.admin_id == 42
    assert entry.before_data == {"name": "旧名称"}
    assert entry.after_data == {"name": "新名称"}
    assert entry.ip == "127.0.0.1"
    assert entry.user_agent == "pytest"
    structlog.contextvars.clear_contextvars()
