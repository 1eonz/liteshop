"""营销仓储。"""

from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.marketing import Coupon, CouponClaim


class MarketingRepository:
    """封装优惠券查询和领取写入。"""

    async def list_coupons(self, session: AsyncSession) -> list[Coupon]:
        """按创建时间倒序读取优惠券。"""
        result = await session.scalars(select(Coupon).order_by(Coupon.created_at.desc(), Coupon.id))
        return list(result.all())

    async def get_coupon(self, session: AsyncSession, code: str, *, for_update: bool = False) -> Coupon | None:
        """按编码读取优惠券。"""
        statement = select(Coupon).where(Coupon.code == code.upper())
        if for_update:
            statement = statement.with_for_update()
        return cast(Coupon | None, await session.scalar(statement))

    async def add_coupon(self, session: AsyncSession, coupon: Coupon) -> Coupon:
        """新增优惠券。"""
        session.add(coupon)
        await session.flush()
        return coupon

    async def get_claim(self, session: AsyncSession, coupon_id: int, user_id: int) -> CouponClaim | None:
        """读取用户领取记录。"""
        return cast(
            CouponClaim | None,
            await session.scalar(
                select(CouponClaim).where(CouponClaim.coupon_id == coupon_id, CouponClaim.user_id == user_id)
            ),
        )

    async def add_claim(self, session: AsyncSession, claim: CouponClaim) -> CouponClaim:
        """新增领取记录。"""
        session.add(claim)
        await session.flush()
        return claim
