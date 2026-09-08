"""售后单模型。"""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class AfterSale(Base):
    """订单项级售后聚合，状态变化必须经售后服务完成。"""

    __tablename__ = "after_sales"
    __table_args__ = (
        UniqueConstraint("order_item_id", "active_key", name="uq_after_sales_active_item"),
        UniqueConstraint("user_id", "client_request_id", name="uq_after_sales_user_request"),
        CheckConstraint("amount_cents > 0", name="ck_after_sales_amount_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    after_sale_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(24), default="PENDING_REVIEW", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    evidence_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    return_address: Mapped[str] = mapped_column(Text, default="")
    return_tracking_no: Mapped[str] = mapped_column(String(100), default="")
    audit_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refund_id: Mapped[int | None] = mapped_column(ForeignKey("refunds.id"), nullable=True, index=True)
    client_request_id: Mapped[str] = mapped_column(String(64), index=True)
    active_key: Mapped[str | None] = mapped_column(String(20), default="ACTIVE", nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
