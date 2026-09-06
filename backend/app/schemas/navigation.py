"""官网导航菜单 DTO。"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class NavigationItemCreate(BaseModel):
    """创建导航项请求。"""

    label: str = Field(min_length=1, max_length=100)
    href: str = Field(min_length=1, max_length=500)
    location: Literal["header", "footer"] = "header"
    kind: Literal["internal", "external", "anchor"] = "internal"
    open_new_tab: bool = Field(default=False, alias="openNewTab")
    sort_order: int = Field(default=0, ge=0, alias="sortOrder")
    enabled: bool = True

    model_config = {"populate_by_name": True}

    @field_validator("href")
    @classmethod
    def validate_href(cls, value: str) -> str:
        """拒绝脚本协议导航。"""
        normalized = value.strip()
        if normalized.lower().startswith(("javascript:", "data:")):
            raise ValueError("导航地址不安全")
        return normalized


class NavigationItemUpdate(NavigationItemCreate):
    """更新导航项请求。"""


class NavigationItemResponse(BaseModel):
    """导航项响应。"""

    id: int
    label: str
    href: str
    location: str
    kind: str
    open_new_tab: bool = Field(alias="openNewTab")
    sort_order: int = Field(alias="sortOrder")
    enabled: bool

    model_config = {"populate_by_name": True}
