"""认证 API DTO。"""

from pydantic import BaseModel, Field


class SmsCodeRequest(BaseModel):
    """短信验证码请求。"""

    phone: str = Field(min_length=6, max_length=32)
    purpose: str = Field(default="login", max_length=32)


class LoginRequest(BaseModel):
    """手机号登录请求。"""

    phone: str = Field(min_length=6, max_length=32)
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")
