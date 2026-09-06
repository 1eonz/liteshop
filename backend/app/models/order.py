"""订单、订单项和支付单模型。"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base

if TYPE_CHECKING:
    from .refund import Refund


class Order(Base):
    """订单正向交易聚合，金额字段全部使用整数分。"""

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("user_id", "client_request_id", name="uq_orders_user_request"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        CheckConstraint("product_amount >= 0", name="ck_orders_product_nonnegative"),
        CheckConstraint("freight_amount >= 0", name="ck_orders_freight_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("paid_amount IS NULL OR paid_amount >= 0", name="ck_orders_paid_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), index=True, default="PENDING_PAYMENT")
    refund_status: Mapped[str] = mapped_column(String(20), index=True, default="NONE")
    total_amount: Mapped[int] = mapped_column(Integer)
    product_amount: Mapped[int] = mapped_column(Integer)
    freight_amount: Mapped[int] = mapped_column(Integer, default=0)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    paid_amount: Mapped[int | None] = mapped_column(Integer, nullable=True)
    address_snapshot: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    remark: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_request_id: Mapped[str] = mapped_column(String(64), index=True)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    shipping_company_code: Mapped[str] = mapped_column(String(20), default="")
    tracking_no: Mapped[str] = mapped_column(String(100), default="")
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """订单商品快照，历史订单不依赖实时商品数据。"""

    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("price_cents >= 0", name="ck_order_items_price_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_order_items_total_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    sku_id: Mapped[int] = mapped_column(ForeignKey("skus.id"), index=True)
    product_id: Mapped[int] = mapped_column(Integer)
    product_name: Mapped[str] = mapped_column(String(200))
    sku_code: Mapped[str] = mapped_column(String(50))
    sku_name: Mapped[str] = mapped_column(String(160))
    spec_values: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    product_image: Mapped[str] = mapped_column(String(500), default="")
    quantity: Mapped[int] = mapped_column(Integer)
    price_cents: Mapped[int] = mapped_column(Integer)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    discount_amount: Mapped[int] = mapped_column(Integer, default=0)
    total_amount: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship(back_populates="items")


class Payment(Base):
    """支付单，渠道交易号和回调 ID 具备幂等约束。"""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", "client_request_id", name="uq_payments_order_request"),
        CheckConstraint("amount_cents >= 0", name="ck_payments_amount_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_no: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    transaction_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    callback_id: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    callback_raw: Mapped[str] = mapped_column(Text, default="")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fail_reason: Mapped[str] = mapped_column(String(500), default="")
    client_request_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship(back_populates="payments")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="payment", cascade="all, delete-orphan")
