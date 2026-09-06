"""支付退款记录模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .order import Payment


class Refund(Base):
    """退款申请及支付渠道退款结果快照。"""

    __tablename__ = "refunds"
    __table_args__ = (
        UniqueConstraint("payment_id", "client_request_id", name="uq_refunds_payment_request"),
        CheckConstraint("amount_cents >= 0", name="ck_refunds_amount_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    refund_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True)
    transaction_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True)
    refund_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fail_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    provider_response: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    client_request_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payment: Mapped["Payment"] = relationship(back_populates="refunds")
