"""JWT 创建与校验工具。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

from .config import settings


@dataclass(frozen=True)
class RefreshTokenClaims:
    """已验证 refresh token 的主体和唯一会话 ID。"""

    subject: str
    jti: str


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    """创建包含类型、过期时间和唯一 ID 的 HS256 JWT。"""
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": uuid4().hex,
    }
    return str(jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm))


def create_access_token(subject: str) -> str:
    """创建两小时有效的 access token。"""
    return _create_token(subject, "access", timedelta(minutes=settings.access_token_expire_minutes))


def create_refresh_token(subject: str) -> str:
    """创建七天有效的 refresh token。"""
    return _create_token(subject, "refresh", timedelta(days=settings.refresh_token_expire_days))


def verify_token(token: str, expected_type: str) -> str | None:
    """校验 JWT 签名、过期时间和令牌类型。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    subject = payload.get("sub")
    return str(subject) if subject else None


def verify_refresh_token_claims(token: str) -> RefreshTokenClaims | None:
    """校验 refresh token 并返回用于轮换的 jti。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
    if payload.get("type") != "refresh":
        return None
    subject = payload.get("sub")
    jti = payload.get("jti")
    if not subject or not jti:
        return None
    return RefreshTokenClaims(subject=str(subject), jti=str(jti))


def verify_access_token(token: str) -> str | None:
    """校验 access token。"""
    return verify_token(token, "access")


def verify_refresh_token(token: str) -> str | None:
    """校验 refresh token。"""
    return verify_token(token, "refresh")
