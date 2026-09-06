"""营销工具请求 DTO。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CouponCreate(BaseModel):
    """创建优惠券，金额单位为分。"""

    code: str = Field(min_length=3, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    coupon_type: Literal["FULL_REDUCTION", "DISCOUNT", "NO_THRESHOLD"] = Field(
        default="FULL_REDUCTION", alias="couponType"
    )
    threshold_cents: int = Field(default=0, ge=0, alias="thresholdCents")
    discount_cents: int = Field(default=0, ge=0, alias="discountCents")
    discount_percent: int | None = Field(default=None, ge=1, le=100, alias="discountPercent")
    total_count: int = Field(default=0, ge=0, alias="totalCount")
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime = Field(alias="endsAt")
    enabled: bool = True
    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_window_and_discount(self) -> "CouponCreate":
        """确保时间窗口和优惠方式合理。"""
        if self.ends_at <= self.starts_at:
            raise ValueError("优惠券结束时间必须晚于开始时间")
        if self.coupon_type == "DISCOUNT" and self.discount_percent is None:
            raise ValueError("折扣券必须提供 discountPercent")
        if self.coupon_type != "DISCOUNT" and self.discount_cents == 0 and self.coupon_type != "NO_THRESHOLD":
            raise ValueError("满减券必须提供 discountCents")
        return self


class CouponClaimRequest(BaseModel):
    """领取优惠券请求。"""

    coupon_code: str = Field(min_length=3, max_length=40, alias="couponCode")
    model_config = {"populate_by_name": True}


class CouponResponse(BaseModel):
    """优惠券响应。"""

    id: int
    code: str
    name: str
    coupon_type: str = Field(alias="couponType")
    threshold_cents: int = Field(alias="thresholdCents")
    discount_cents: int = Field(alias="discountCents")
    discount_percent: int | None = Field(alias="discountPercent")
    total_count: int = Field(alias="totalCount")
    claimed_count: int = Field(alias="claimedCount")
    used_count: int = Field(alias="usedCount")
    starts_at: datetime = Field(alias="startsAt")
    ends_at: datetime = Field(alias="endsAt")
    enabled: bool
    model_config = {"populate_by_name": True}
