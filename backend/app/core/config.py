"""应用配置，仅从环境变量读取敏感值。"""

import os
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    jwt_secret: str = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    refresh_token_expire_days: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://liteshop:liteshop@localhost:5432/liteshop_dev")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    idempotency_ttl_seconds: int = int(os.getenv("IDEMPOTENCY_TTL_SECONDS", "300"))
    payment_callback_secret: str = os.getenv("PAYMENT_CALLBACK_SECRET") or secrets.token_urlsafe(32)
    # 渠道密钥未单独配置时回退到旧的全局密钥，便于开发环境平滑升级。
    payment_wechat_callback_secret: str = os.getenv("PAYMENT_WECHAT_CALLBACK_SECRET") or payment_callback_secret
    payment_alipay_callback_secret: str = os.getenv("PAYMENT_ALIPAY_CALLBACK_SECRET") or payment_callback_secret
    oss_provider: str = os.getenv("OSS_PROVIDER", "local")
    oss_access_key_id: str = os.getenv("OSS_ACCESS_KEY_ID", "")
    oss_access_key_secret: str = os.getenv("OSS_ACCESS_KEY_SECRET", "")
    oss_bucket: str = os.getenv("OSS_BUCKET", "")
    oss_region: str = os.getenv("OSS_REGION", "")
    oss_cdn_domain: str = os.getenv("OSS_CDN_DOMAIN", "http://localhost:8000")
    upload_max_size_bytes: int = int(os.getenv("UPLOAD_MAX_SIZE_BYTES", "10485760"))
    upload_allowed_mime_types: tuple[str, ...] = tuple(
        mime.strip()
        for mime in os.getenv("UPLOAD_ALLOWED_MIME_TYPES", "image/jpeg,image/png,image/webp,image/gif").split(",")
        if mime.strip()
    )
    use_database: bool = os.getenv("LITESHOP_USE_DATABASE", "false").lower() == "true"
    environment: str = os.getenv("ENV", "development")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax")
    sms_phone_daily_limit: int = int(os.getenv("RATE_LIMIT_SMS_PHONE_PER_DAY", "5"))
    login_phone_five_minute_limit: int = int(os.getenv("RATE_LIMIT_LOGIN_USER_PER_5MIN", "5"))
    login_ip_hourly_limit: int = int(os.getenv("RATE_LIMIT_LOGIN_IP_PER_HOUR", "20"))
    trusted_proxy_networks: tuple[str, ...] = tuple(
        network.strip() for network in os.getenv("TRUSTED_PROXY_NETWORKS", "").split(",") if network.strip()
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if origin.strip()
    )
    nextjs_base_url: str = os.getenv("NEXTJS_BASE_URL", "")
    revalidate_token: str = os.getenv("REVALIDATE_TOKEN", "")
    revalidate_timeout_seconds: float = float(os.getenv("REVALIDATE_TIMEOUT_SECONDS", "2"))

    def payment_callback_secret_for(self, provider: str) -> str:
        """按支付渠道读取回调密钥，未知渠道不允许回退。"""
        normalized = provider.upper()
        if normalized == "WECHAT":
            return self.payment_wechat_callback_secret
        if normalized == "ALIPAY":
            return self.payment_alipay_callback_secret
        raise ValueError(f"不支持的支付渠道: {provider}")

    def __post_init__(self) -> None:
        """预发布和生产环境禁止使用进程生成的临时密钥。"""
        if self.environment in {"staging", "production"}:
            if not self.use_database:
                raise ValueError("预发布和生产环境必须启用 LITESHOP_USE_DATABASE")
            if not os.getenv("JWT_SECRET") or len(self.jwt_secret) < 32:
                raise ValueError("JWT_SECRET 必须通过环境变量提供且长度不少于 32")
            has_global_secret = bool(os.getenv("PAYMENT_CALLBACK_SECRET"))
            has_channel_secrets = bool(os.getenv("PAYMENT_WECHAT_CALLBACK_SECRET")) and bool(
                os.getenv("PAYMENT_ALIPAY_CALLBACK_SECRET")
            )
            if not has_global_secret and not has_channel_secrets:
                raise ValueError("必须配置 PAYMENT_CALLBACK_SECRET，或同时配置两个渠道回调密钥")
            if any(
                len(secret) < 32
                for secret in (
                    self.payment_callback_secret,
                    self.payment_wechat_callback_secret,
                    self.payment_alipay_callback_secret,
                )
            ):
                raise ValueError("支付回调密钥长度必须不少于 32")


settings = Settings()
