"""营销工具领域模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Coupon(Base):
    """优惠券定义，金额字段全部使用整数分。"""

    __tablename__ = "coupons"
    __table_args__ = (UniqueConstraint("code", name="uq_coupons_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120))
    coupon_type: Mapped[str] = mapped_column(String(20), default="FULL_REDUCTION")
    threshold_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_cents: Mapped[int] = mapped_column(Integer, default=0)
    discount_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    claimed_count: Mapped[int] = mapped_column(Integer, default=0)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CouponClaim(Base):
    """用户领取记录，保证同一用户同一券只领取一次。"""

    __tablename__ = "coupon_claims"
    __table_args__ = (UniqueConstraint("coupon_id", "user_id", name="uq_coupon_claims_coupon_user"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
