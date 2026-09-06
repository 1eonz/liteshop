"""LiteShop FastAPI 应用入口。"""

from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.admin import router as admin_router
from .api.auth import router as auth_router
from .api.cart import router as cart_router
from .api.favorites import router as favorites_router
from .api.health import router as health_router
from .api.notifications import router as notifications_router
from .api.orders import router as orders_router
from .api.pages import router as pages_router
from .api.products import router as products_router
from .api.reviews import router as reviews_router
from .api.settings import router as settings_router
from .api.uploads import router as uploads_router
from .api.users import router as users_router
from .core.config import settings
from .core.logging import configure_logging, get_logger
from .core.network import get_client_ip
from .core.security import verify_access_token
from .errors import ApiError

configure_logging()
logger = get_logger()
app = FastAPI(title="LiteShop API", version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(orders_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(reviews_router, prefix="/api/v1")
app.include_router(pages_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(favorites_router, prefix="/api/v1")
app.include_router(uploads_router, prefix="/api/v1")
app.include_router(health_router)


@app.middleware("http")
async def request_context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """传播客户端请求 ID，并为缺失值生成唯一标识。"""
    request_id = request.headers.get("X-Request-Id") or uuid4().hex
    request.state.request_id = request_id
    authorization = request.headers.get("authorization", "")
    token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    user_id = verify_access_token(token) or ""
    client_ip = get_client_ip(request)
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id,
        user_id=user_id,
        ip=client_ip,
        user_agent=request.headers.get("user-agent", ""),
    )
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        raise
    else:
        logger.info(
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        response.headers["X-Request-Id"] = request_id
        return response
    finally:
        structlog.contextvars.clear_contextvars()


@app.exception_handler(ApiError)
async def api_error_handler(request: Request, error: ApiError) -> JSONResponse:
    """按错误码契约输出统一错误响应。"""
    content: dict[str, object] = {
        "code": error.code,
        "i18nKey": error.i18n_key,
        "message": error.message,
        "requestId": getattr(request.state, "request_id", uuid4().hex),
    }
    if error.field is not None:
        content["field"] = error.field
    if error.details is not None:
        content["details"] = error.details
    return JSONResponse(status_code=error.status_code, content=content, headers=error.headers)
