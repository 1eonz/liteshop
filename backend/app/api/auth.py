"""短信登录与 JWT 刷新接口。"""

from typing import Literal, NoReturn

from fastapi import APIRouter, Request, Response

from ..core.config import settings
from ..core.database import transaction
from ..core.network import get_client_ip
from ..core.rate_limit import RateLimitExceeded, rate_limiter
from ..core.security import create_access_token, create_refresh_token, verify_refresh_token_claims
from ..core.token_store import TokenStoreUnavailable, refresh_token_store
from ..errors import ApiError
from ..schemas.auth import LoginRequest, SmsCodeRequest
from ..services.auth import AuthenticationError, SmsUnavailable, auth_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_COOKIE_NAME = "refresh_token"


def _cookie_samesite() -> Literal["lax", "strict", "none"]:
    """把环境变量收敛为 Starlette 支持的 SameSite 值。"""
    value = settings.cookie_samesite.lower()
    if value == "strict":
        return "strict"
    if value == "none":
        return "none"
    return "lax"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """设置仅服务端可读的刷新令牌 Cookie。"""
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=_cookie_samesite(),
        path="/api/v1/auth",
    )


def _validate_cookie_origin(request: Request) -> None:
    """Cookie 写接口只接受配置的前端来源。"""
    origin = request.headers.get("origin")
    if origin not in settings.cors_origins:
        raise ApiError(
            status_code=403,
            code=40301,
            i18n_key="common.forbidden",
            message="请求来源不受信任",
        )


def _raise_authentication_error(error: AuthenticationError) -> NoReturn:
    """把认证领域异常映射为统一 API 错误。"""
    if str(error) == "SMS_RATE_LIMITED":
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="验证码发送过于频繁，请稍后再试",
        ) from error
    if str(error) == "USER_DISABLED":
        raise ApiError(
            status_code=403,
            code=40301,
            i18n_key="common.forbidden",
            message="用户已被停用",
        ) from error
    raise ApiError(
        status_code=401,
        code=40101,
        i18n_key="auth.unauthorized",
        message="验证码错误或已过期",
        field="code",
    ) from error


async def _send_code(payload: SmsCodeRequest) -> dict[str, object]:
    """执行短信验证码发送并统一处理服务异常。"""
    try:
        await auth_service.send_sms_code(payload.phone)
    except AuthenticationError as error:
        _raise_authentication_error(error)
    except SmsUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="短信服务暂不可用",
        ) from error
    except TokenStoreUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="认证服务暂不可用",
        ) from error
    return {"sent": True, "purpose": payload.purpose}


def _client_ip(request: Request) -> str:
    """提取限流使用的客户端 IP。"""
    return get_client_ip(request)


async def _check_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    """执行限流并映射统一错误响应。"""
    try:
        await rate_limiter.check(
            key,
            limit=limit,
            window_seconds=window_seconds,
            use_redis=settings.use_database,
        )
    except RateLimitExceeded as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求过于频繁，请稍后重试",
            headers={"Retry-After": str(error.retry_after)},
        ) from error


async def _check_sms_limits(phone: str, request: Request) -> None:
    """执行手机号分钟/日限额和 IP 小时限额。"""
    await _check_rate_limit(f"sms:phone:minute:{phone}", limit=1, window_seconds=60)
    await _check_rate_limit(
        f"sms:phone:day:{phone}",
        limit=settings.sms_phone_daily_limit,
        window_seconds=24 * 60 * 60,
    )
    await _check_rate_limit(f"sms:ip:hour:{_client_ip(request)}", limit=10, window_seconds=60 * 60)


async def _check_login_limits(phone: str, request: Request) -> None:
    """执行登录手机号五分钟与 IP 小时限额。"""
    await _check_rate_limit(
        f"login:phone:{phone}",
        limit=settings.login_phone_five_minute_limit,
        window_seconds=5 * 60,
    )
    await _check_rate_limit(
        f"login:ip:{_client_ip(request)}",
        limit=settings.login_ip_hourly_limit,
        window_seconds=60 * 60,
    )


@router.post("/sms-code")
async def send_sms_code(payload: SmsCodeRequest, request: Request) -> dict[str, object]:
    """发送登录验证码。"""
    await _check_sms_limits(payload.phone, request)
    return success(await _send_code(payload))


@router.post("/sms/send", deprecated=True)
async def send_sms_code_compatibility(payload: SmsCodeRequest, request: Request) -> dict[str, object]:
    """兼容旧客户端的短信验证码路径。"""
    await _check_sms_limits(payload.phone, request)
    return success(await _send_code(payload))


@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, object]:
    """使用手机号验证码登录并签发双令牌。"""
    await _check_login_limits(payload.phone, request)
    try:
        if settings.use_database:
            async with transaction() as session:
                subject, access_token, refresh_token = await auth_service.login(
                    session,
                    payload.phone,
                    payload.code,
                )
        else:
            subject, access_token, refresh_token = await auth_service.login(
                None,
                payload.phone,
                payload.code,
            )
    except AuthenticationError as error:
        _raise_authentication_error(error)
    except SmsUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="短信服务暂不可用",
        ) from error
    except TokenStoreUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="认证服务暂不可用",
        ) from error

    _set_refresh_cookie(response, refresh_token)
    return success(
        {
            "accessToken": access_token,
            "tokenType": "bearer",
            "expiresIn": settings.access_token_expire_minutes * 60,
            "subject": subject,
        }
    )


@router.post("/refresh")
async def refresh_token(request: Request, response: Response) -> dict[str, object]:
    """校验并轮换刷新令牌。"""
    authorization = request.headers.get("authorization", "")
    bearer_token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    cookie_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if cookie_token:
        _validate_cookie_origin(request)
    current_refresh_token = cookie_token or bearer_token
    claims = verify_refresh_token_claims(current_refresh_token or "")
    if claims is None:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="刷新令牌无效或已过期",
        )
    access_token = create_access_token(claims.subject)
    next_refresh_token = create_refresh_token(claims.subject)
    next_claims = verify_refresh_token_claims(next_refresh_token)
    if next_claims is None:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="认证服务暂不可用",
        )
    try:
        rotated = await refresh_token_store.rotate(
            claims.jti,
            next_claims.jti,
            claims.subject,
            settings.refresh_token_expire_days * 24 * 60 * 60,
        )
    except TokenStoreUnavailable as error:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="认证服务暂不可用",
        ) from error
    if not rotated:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="刷新令牌已使用或已撤销",
        )
    _set_refresh_cookie(response, next_refresh_token)
    return success(
        {
            "accessToken": access_token,
            "tokenType": "bearer",
            "expiresIn": settings.access_token_expire_minutes * 60,
        }
    )


@router.post("/logout")
async def logout(request: Request, response: Response, _subject: CurrentSubject) -> dict[str, object]:
    """撤销当前刷新令牌并清除 Cookie；access token 由短有效期自然失效。"""
    cookie_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if cookie_token:
        _validate_cookie_origin(request)
    authorization = request.headers.get("authorization", "")
    bearer_token = authorization.removeprefix("Bearer ").strip() if authorization.startswith("Bearer ") else ""
    refresh_token = cookie_token or bearer_token
    claims = verify_refresh_token_claims(refresh_token) if refresh_token else None
    if claims is not None:
        try:
            await refresh_token_store.revoke(claims.jti)
        except TokenStoreUnavailable as error:
            raise ApiError(
                status_code=503,
                code=50001,
                i18n_key="common.internal_error",
                message="认证服务暂不可用",
            ) from error
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/api/v1/auth")
    return success({"loggedOut": True})
