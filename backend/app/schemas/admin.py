"""管理后台写操作 DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field


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
