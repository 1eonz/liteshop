"""官网联系表单 DTO。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ContactFormCreate(BaseModel):
    """联系表单提交请求。"""

    name: str = Field(min_length=1, max_length=100)
    email: str = Field(max_length=320)
    phone: str = Field(default="", max_length=30)
    company: str = Field(default="", max_length=200)
    message: str = Field(min_length=1, max_length=5000)
    website: str = Field(default="", max_length=200)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        """使用轻量规则校验邮箱，避免引入额外运行时依赖。"""
        normalized = value.strip()
        if not normalized or "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("邮箱格式不正确")
        return normalized


class ContactFormResponse(BaseModel):
    """联系表单受理响应。"""

    id: int
    status: str
    accepted: bool = True


class ContactFormStatusUpdate(BaseModel):
    """后台更新联系表单处理状态。"""

    status: Literal["NEW", "IN_PROGRESS", "RESOLVED", "SPAM"]
