"""管理后台写操作 DTO。"""

import re
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

_PHONE_PATTERN = re.compile(r"^\+?(?=(?:[^0-9]*[0-9]){6,20}[^0-9]*$)[0-9][0-9 -]*$")


def validate_address_snapshot(value: dict[str, str]) -> dict[str, str]:
    """校验订单地址快照，兼容驼峰和下划线字段名。"""
    aliases = {
        "receiverName": "receiver_name",
        "receiver_name": "receiver_name",
        "phone": "phone",
        "detail": "detail",
    }
    normalized: dict[str, str] = {}
    for key, canonical in aliases.items():
        if key in value:
            field_value = value[key]
            if not isinstance(field_value, str):
                raise ValueError(f"地址字段 {key} 必须是字符串")
            normalized.setdefault(canonical, field_value.strip())
    required = ("receiver_name", "phone", "detail")
    missing = [field for field in required if not normalized.get(field)]
    if missing:
        raise ValueError(f"地址缺少必填字段: {', '.join(missing)}")
    receiver_name = normalized["receiver_name"]
    phone = normalized["phone"]
    detail = normalized["detail"]
    if len(receiver_name) > 50:
        raise ValueError("收货人姓名长度不能超过 50 个字符")
    if not 6 <= len(phone) <= 20 or _PHONE_PATTERN.fullmatch(phone) is None:
        raise ValueError("手机号格式不正确")
    if len(detail) > 500:
        raise ValueError("详细地址长度不能超过 500 个字符")
    return value


class ShipOrderRequest(BaseModel):
    """订单发货请求。"""

    logistics_company_code: Annotated[str, Field(alias="logisticsCompanyCode", min_length=1, max_length=20)]
    tracking_no: Annotated[str, Field(alias="trackingNo", min_length=1, max_length=100)]
    model_config = {"populate_by_name": True}


class OrderPriceUpdate(BaseModel):
    """待付款订单改价请求，金额单位为分。"""

    total_amount: Annotated[int, Field(alias="totalAmount", ge=0)]
    model_config = {"populate_by_name": True}


class OrderManagementUpdate(BaseModel):
    """后台订单备注和地址快照更新请求。"""

    remark: str | None = Field(default=None, max_length=500)
    address_snapshot: dict[str, str] | None = Field(default=None, alias="addressSnapshot")
    model_config = {"populate_by_name": True}

    @field_validator("address_snapshot")
    @classmethod
    def validate_address(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        """后台地址修改必须包含完整且格式正确的收货地址。"""
        if value is None:
            return None
        return validate_address_snapshot(value)


class FeatureFlagUpdate(BaseModel):
    """功能开关更新请求。"""

    enabled: bool


class ThemeSettingsUpdate(BaseModel):
    """商城主题配置，值由设计令牌名称约束。"""

    primary_color: str = Field(alias="primaryColor", pattern=r"^#[0-9a-fA-F]{6}$")
    navigation_style: str = Field(alias="navigationStyle", pattern=r"^(glass|solid)$")
    tabbar_style: str = Field(alias="tabbarStyle", pattern=r"^(gallery|minimal)$")
    model_config = {"populate_by_name": True}


class SiteSettingsUpdate(BaseModel):
    """官网全局设置，脚本字段不在此接口开放。"""

    site_name: str = Field(default="LiteShop", min_length=1, max_length=100, alias="siteName")
    logo_url: str = Field(default="", max_length=500, alias="logoUrl")
    favicon_url: str = Field(default="", max_length=500, alias="faviconUrl")
    default_title: str = Field(default="LiteShop", max_length=200, alias="defaultTitle")
    default_description: str = Field(default="", max_length=500, alias="defaultDescription")
    allow_dark_mode: bool = Field(default=False, alias="allowDarkMode")
    animation_enabled: bool = Field(default=True, alias="animationEnabled")

    model_config = {"populate_by_name": True}


class RoleCreate(BaseModel):
    """创建后台角色及其权限点。"""

    name: str = Field(min_length=1, max_length=64)
    permission_codes: list[str] = Field(default_factory=list, alias="permissionCodes", max_length=100)

    model_config = {"populate_by_name": True}


class RoleUpdate(BaseModel):
    """更新后台角色名称和权限点。"""

    name: str | None = Field(default=None, min_length=1, max_length=64)
    permission_codes: list[str] | None = Field(default=None, alias="permissionCodes", max_length=100)

    model_config = {"populate_by_name": True}


class UserRolesUpdate(BaseModel):
    """覆盖指定管理员的角色集合。"""

    role_ids: list[int] = Field(default_factory=list, alias="roleIds", max_length=20)

    model_config = {"populate_by_name": True}
