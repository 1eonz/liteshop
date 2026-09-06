"""创建库存流水、订单、订单项、支付和数据库幂等表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_140700"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建交易链路持久化表和原子库存审计字段。"""
    op.create_table(
        "stock_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("physical_before", sa.Integer(), nullable=False),
        sa.Column("physical_after", sa.Integer(), nullable=False),
        sa.Column("locked_before", sa.Integer(), nullable=False),
        sa.Column("locked_after", sa.Integer(), nullable=False),
        sa.Column("reference_no", sa.String(64), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(64), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_stock_logs_sku_id", "stock_logs", ["sku_id"])
    op.create_index("ix_stock_logs_event_type", "stock_logs", ["event_type"])
    op.create_index("ix_stock_logs_request_id", "stock_logs", ["request_id"])
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_no", sa.String(32), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING_PAYMENT"),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("product_amount", sa.Integer(), nullable=False),
        sa.Column("freight_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Integer(), nullable=True),
        sa.Column("address_snapshot", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("client_request_id", sa.String(64), nullable=False),
        sa.Column("expired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipping_company_code", sa.String(20), nullable=False, server_default=""),
        sa.Column("tracking_no", sa.String(100), nullable=False, server_default=""),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "client_request_id", name="uq_orders_user_request"),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        sa.CheckConstraint("product_amount >= 0", name="ck_orders_product_nonnegative"),
        sa.CheckConstraint("freight_amount >= 0", name="ck_orders_freight_nonnegative"),
        sa.CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonnegative"),
    )
    op.create_index("ix_orders_order_no", "orders", ["order_no"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_client_request_id", "orders", ["client_request_id"])
    op.create_index("ix_orders_expired_at", "orders", ["expired_at"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sku_id", sa.Integer(), sa.ForeignKey("skus.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(200), nullable=False),
        sa.Column("sku_code", sa.String(50), nullable=False),
        sa.Column("sku_name", sa.String(160), nullable=False),
        sa.Column("spec_values", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("product_image", sa.String(500), nullable=False, server_default=""),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("discount_amount", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_amount", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("price_cents >= 0", name="ck_order_items_price_nonnegative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_order_items_total_nonnegative"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_sku_id", "order_items", ["sku_id"])
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_no", sa.String(32), nullable=False, unique=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("transaction_id", sa.String(128), nullable=True, unique=True),
        sa.Column("callback_id", sa.String(128), nullable=True, unique=True),
        sa.Column("callback_raw", sa.Text(), nullable=False, server_default=""),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fail_reason", sa.String(500), nullable=False, server_default=""),
        sa.Column("client_request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("order_id", "client_request_id", name="uq_payments_order_request"),
        sa.CheckConstraint("amount_cents >= 0", name="ck_payments_amount_nonnegative"),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])
    op.create_index("ix_payments_payment_no", "payments", ["payment_no"])
    op.create_index("ix_payments_user_id", "payments", ["user_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_client_request_id", "payments", ["client_request_id"])
    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("action_type", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "request_id", "action_type", name="uq_idempotency_action"),
    )
    op.create_index("ix_idempotency_records_user_id", "idempotency_records", ["user_id"])
    op.create_index("ix_idempotency_records_request_id", "idempotency_records", ["request_id"])


def downgrade() -> None:
    """按外键依赖反向删除交易表。"""
    op.drop_index("ix_idempotency_records_request_id", table_name="idempotency_records")
    op.drop_index("ix_idempotency_records_user_id", table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index("ix_payments_client_request_id", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_user_id", table_name="payments")
    op.drop_index("ix_payments_payment_no", table_name="payments")
    op.drop_index("ix_payments_order_id", table_name="payments")
    op.drop_table("payments")
    op.drop_index("ix_order_items_sku_id", table_name="order_items")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_expired_at", table_name="orders")
    op.drop_index("ix_orders_client_request_id", table_name="orders")
    op.drop_index("ix_orders_status", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_stock_logs_request_id", table_name="stock_logs")
    op.drop_index("ix_stock_logs_event_type", table_name="stock_logs")
    op.drop_index("ix_stock_logs_sku_id", table_name="stock_logs")
    op.drop_table("stock_logs")
