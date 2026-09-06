"""商品评价业务服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.review import ProductReview
from ..repositories.review import ReviewRepository


class ReviewError(ValueError):
    """评价校验失败。"""


class ReviewService:
    """编排购买资格、幂等创建和审核状态。"""

    def __init__(self, repository: ReviewRepository | None = None) -> None:
        self.repository = repository or ReviewRepository()

    async def create(
        self, session: AsyncSession, user_id: int, order_item_id: int, rating: int, content: str, images: list[str]
    ) -> ProductReview:
        """仅允许已完成订单且未评价的订单项提交评价。"""
        existing = await self.repository.get_by_order_item(session, order_item_id)
        if existing is not None:
            if existing.user_id == user_id:
                return existing
            raise ReviewError("订单项评价不存在")
        item = await self.repository.get_order_item_for_user(session, order_item_id, user_id)
        if item is None:
            raise ReviewError("只有已完成订单的购买者可以评价")
        return await self.repository.create(session, item, user_id, rating, content, images)

    async def list_product(self, session: AsyncSession, product_id: int) -> dict[str, object]:
        """只返回审核通过的评价。"""
        reviews, average = await self.repository.list_approved(session, product_id)
        return {
            "averageRating": round(average, 2),
            "items": [
                {
                    "id": review.id,
                    "rating": review.rating,
                    "content": review.content,
                    "images": list(review.images),
                    "createdAt": review.created_at.isoformat(),
                }
                for review in reviews
            ],
        }

    async def audit(self, session: AsyncSession, review_id: int, status: str, reason: str) -> dict[str, object]:
        """审核评价并保留原因。"""
        review = await session.get(ProductReview, review_id, with_for_update=True)
        if review is None:
            raise ReviewError("评价不存在")
        if review.status not in {"PENDING", "REJECTED"}:
            raise ReviewError("评价当前不可审核")
        review.status = status
        review.audit_reason = reason or None
        review.updated_at = datetime.now(UTC)
        await session.flush()
        return {"id": review.id, "status": review.status, "reason": review.audit_reason}


review_service = ReviewService()
