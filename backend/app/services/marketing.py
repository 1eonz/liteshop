"""优惠券业务服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.marketing import Coupon, CouponClaim
from ..repositories.marketing import MarketingRepository
from ..schemas.marketing import CouponCreate


class CouponError(ValueError):
    """优惠券业务规则错误。"""


class MarketingService:
    """编排优惠券创建、查询和领取。"""

    def __init__(self, repository: MarketingRepository | None = None) -> None:
        self.repository = repository or MarketingRepository()

    @staticmethod
    def response(coupon: Coupon) -> dict[str, object]:
        """映射优惠券响应。"""
        return {
            "id": coupon.id,
            "code": coupon.code,
            "name": coupon.name,
            "couponType": coupon.coupon_type,
            "thresholdCents": coupon.threshold_cents,
            "discountCents": coupon.discount_cents,
            "discountPercent": coupon.discount_percent,
            "totalCount": coupon.total_count,
            "claimedCount": coupon.claimed_count,
            "usedCount": coupon.used_count,
            "startsAt": coupon.starts_at.isoformat(),
            "endsAt": coupon.ends_at.isoformat(),
            "enabled": coupon.enabled,
        }

    async def list_coupons(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取优惠券列表。"""
        return [self.response(item) for item in await self.repository.list_coupons(session)]

    async def create_coupon(self, session: AsyncSession, payload: CouponCreate) -> dict[str, object]:
        """创建优惠券。"""
        if await self.repository.get_coupon(session, payload.code) is not None:
            raise CouponError("优惠券编码已存在")
        now = datetime.now(UTC)
        coupon = Coupon(
            code=payload.code.upper(),
            name=payload.name,
            coupon_type=payload.coupon_type,
            threshold_cents=payload.threshold_cents,
            discount_cents=payload.discount_cents,
            discount_percent=payload.discount_percent,
            total_count=payload.total_count,
            starts_at=payload.starts_at,
            ends_at=payload.ends_at,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        await self.repository.add_coupon(session, coupon)
        return self.response(coupon)

    async def claim(self, session: AsyncSession, user_id: int, code: str) -> dict[str, object]:
        """锁定优惠券并领取，重复领取返回同一结果。"""
        coupon = await self.repository.get_coupon(session, code, for_update=True)
        if coupon is None:
            raise CouponError("优惠券不存在")
        now = datetime.now(UTC)
        if not coupon.enabled or now < coupon.starts_at or now > coupon.ends_at:
            raise CouponError("优惠券当前不可领取")
        if coupon.total_count > 0 and coupon.claimed_count >= coupon.total_count:
            raise CouponError("优惠券已领完")
        if await self.repository.get_claim(session, coupon.id, user_id) is not None:
            return {"coupon": self.response(coupon), "claimed": True, "duplicate": True}
        coupon.claimed_count += 1
        await self.repository.add_claim(session, CouponClaim(coupon_id=coupon.id, user_id=user_id, claimed_at=now))
        await session.flush()
        return {"coupon": self.response(coupon), "claimed": True, "duplicate": False}


marketing_service = MarketingService()
