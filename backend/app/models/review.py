"""商品评价模型。"""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ProductReview(Base):
    """订单项评价及审核状态。"""

    __tablename__ = "product_reviews"
    __table_args__ = (
        UniqueConstraint("order_item_id", name="uq_product_reviews_order_item"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_product_reviews_rating"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, default="")
    images: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    audit_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    merchant_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    merchant_replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
