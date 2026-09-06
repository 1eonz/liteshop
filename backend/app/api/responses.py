"""API 成功响应构造器。"""

from uuid import uuid4

import structlog


def success(data: object, message: str = "ok") -> dict[str, object]:
    """使用当前请求上下文构造统一成功信封。"""
    request_context = structlog.contextvars.get_contextvars()
    request_id = str(request_context.get("request_id") or uuid4().hex)
    return {"code": 0, "message": message, "data": data, "requestId": request_id}
