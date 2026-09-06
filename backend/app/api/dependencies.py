"""API 层共享认证依赖。"""

from typing import Annotated

from fastapi import Depends, Header

from ..core.security import verify_access_token
from ..errors import ApiError


def get_current_subject(authorization: Annotated[str | None, Header()] = None) -> str:
    """校验 Bearer access token 并返回主体标识。"""
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="未登录或令牌无效",
        )
    subject = verify_access_token(authorization.removeprefix("Bearer ").strip())
    if subject is None:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="未登录或令牌无效",
        )
    return subject


CurrentSubject = Annotated[str, Depends(get_current_subject)]
