"""商品评价仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.order import Order, OrderItem
from ..models.review import ProductReview


class ReviewRepository:
    """封装评价查询、创建和审核。"""

    async def get_by_order_item(self, session: AsyncSession, order_item_id: int) -> ProductReview | None:
        """按订单项查评价。"""
        return cast(
            ProductReview | None,
            await session.scalar(select(ProductReview).where(ProductReview.order_item_id == order_item_id)),
        )

    async def get_order_item_for_user(
        self, session: AsyncSession, order_item_id: int, user_id: int
    ) -> OrderItem | None:
        """读取属于用户且订单已完成的订单项。"""
        return cast(
            OrderItem | None,
            await session.scalar(
                select(OrderItem)
                .join(Order, Order.id == OrderItem.order_id)
                .where(OrderItem.id == order_item_id, Order.user_id == user_id, Order.status == "COMPLETED")
            ),
        )

    async def create(
        self, session: AsyncSession, item: OrderItem, user_id: int, rating: int, content: str, images: list[str]
    ) -> ProductReview:
        """创建待审核评价。"""
        now = datetime.now(UTC)
        review = ProductReview(
            order_item_id=item.id,
            product_id=item.product_id,
            sku_id=item.sku_id,
            user_id=user_id,
            rating=rating,
            content=content,
            images=images,
            status="PENDING",
            created_at=now,
            updated_at=now,
        )
        session.add(review)
        await session.flush()
        return review

    async def list_approved(self, session: AsyncSession, product_id: int) -> tuple[list[ProductReview], float]:
        """返回商品已审核评价和平均分。"""
        result = await session.scalars(
            select(ProductReview)
            .where(ProductReview.product_id == product_id, ProductReview.status == "APPROVED")
            .order_by(ProductReview.created_at.desc())
        )
        average = float(
            await session.scalar(
                select(func.avg(ProductReview.rating)).where(
                    ProductReview.product_id == product_id, ProductReview.status == "APPROVED"
                )
            )
            or 0
        )
        return list(result.all()), average

    async def list_for_audit(self, session: AsyncSession, limit: int = 100) -> list[ProductReview]:
        """后台按时间读取待审核评价。"""
        result = await session.scalars(select(ProductReview).order_by(ProductReview.created_at.desc()).limit(limit))
        return list(result.all())

    async def get_for_update(self, session: AsyncSession, review_id: int) -> ProductReview | None:
        """锁定待审核评价。"""
        return cast(ProductReview | None, await session.get(ProductReview, review_id, with_for_update=True))

    async def flush(self, session: AsyncSession) -> None:
        """刷新审核变更，不提交外层事务。"""
        await session.flush()
