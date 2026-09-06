"""补齐商品规格、订单快照和库存审计字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260905_180000"
down_revision: str | None = "20260905_170000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """以向后兼容方式补齐 E3 数据模型，并保留旧审计列。"""
    # SKU 的外键命名统一为 product_id，旧索引和约束在改名后重建。
    op.drop_constraint("uq_skus_spu_spec_hash", "skus", type_="unique")
    op.alter_column("skus", "spu_id", new_column_name="product_id")
    op.drop_index("ix_skus_spu_id", table_name="skus")
    op.create_index("ix_skus_product_id", "skus", ["product_id"])
    op.create_index("ix_skus_status", "skus", ["status"])
    op.create_unique_constraint("uq_skus_product_spec_hash", "skus", ["product_id", "spec_hash"])

    op.add_column("products", sa.Column("seo_title", sa.String(200), nullable=True))
    op.add_column("products", sa.Column("seo_description", sa.String(500), nullable=True))
    op.add_column("products", sa.Column("seo_keywords", sa.String(200), nullable=True))
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_index("ix_products_name", "products", ["name"])

    op.create_table(
        "product_specs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("product_id", "name", name="uq_product_specs_product_name"),
    )
    op.create_index("ix_product_specs_product_id", "product_specs", ["product_id"])
    op.create_table(
        "product_spec_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("spec_id", sa.Integer(), sa.ForeignKey("product_specs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.String(100), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("spec_id", "value", name="uq_product_spec_values_spec_value"),
    )
    op.create_index("ix_product_spec_values_spec_id", "product_spec_values", ["spec_id"])

    op.add_column("orders", sa.Column("refund_status", sa.String(20), nullable=False, server_default="NONE"))
    op.add_column("orders", sa.Column("remark", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("cancel_reason", sa.String(200), nullable=True))
    # PostgreSQL 不会自动把 TEXT 默认值转换为 JSONB，类型转换前必须先移除旧默认值。
    op.alter_column("orders", "address_snapshot", existing_type=sa.Text(), server_default=None)
    op.alter_column(
        "orders",
        "address_snapshot",
        existing_type=sa.Text(),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=False,
        postgresql_using="address_snapshot::jsonb",
    )
    op.alter_column(
        "orders",
        "address_snapshot",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=sa.text("'{}'::jsonb"),
    )
    op.create_index("ix_orders_refund_status", "orders", ["refund_status"])
    op.create_check_constraint("ck_orders_paid_nonnegative", "orders", "paid_amount IS NULL OR paid_amount >= 0")

    # 旧 event_type/quantity/reference_no 列继续保留，新增规范列并回填历史记录。
    op.add_column("stock_logs", sa.Column("source_type", sa.String(20), nullable=True))
    op.add_column("stock_logs", sa.Column("source_id", sa.Integer(), nullable=True))
    op.add_column("stock_logs", sa.Column("change_type", sa.String(20), nullable=True))
    op.add_column("stock_logs", sa.Column("change_qty", sa.Integer(), nullable=True))
    op.add_column("stock_logs", sa.Column("operator_id", sa.Integer(), nullable=True))
    op.add_column("stock_logs", sa.Column("reason", sa.String(200), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE stock_logs
            SET source_type = CASE event_type
                WHEN 'LOCK' THEN 'ORDER_LOCK'
                WHEN 'DEDUCT' THEN 'ORDER_SHIP'
                WHEN 'RELEASE' THEN 'ORDER_CANCEL'
                WHEN 'PURCHASE_IN' THEN 'PURCHASE'
                ELSE 'MANUAL'
            END,
            change_type = CASE event_type
                WHEN 'LOCK' THEN 'LOCK'
                WHEN 'DEDUCT' THEN 'SHIP'
                WHEN 'RELEASE' THEN 'UNLOCK'
                WHEN 'PURCHASE_IN' THEN 'INBOUND'
                ELSE 'ADJUST'
            END,
            change_qty = quantity,
            source_id = CASE
                WHEN reference_no ~ '^[0-9]+$' THEN reference_no::integer
                ELSE NULL
            END
            """
        )
    )
    op.alter_column("stock_logs", "source_type", existing_type=sa.String(20), nullable=False)
    op.alter_column("stock_logs", "change_type", existing_type=sa.String(20), nullable=False)
    op.alter_column("stock_logs", "change_qty", existing_type=sa.Integer(), nullable=False)
    op.create_index("ix_stock_logs_created_at", "stock_logs", ["created_at"])
    op.create_index("ix_stock_logs_source", "stock_logs", ["source_type", "source_id"])

    # 一期退款接口需要独立退款记录，售后聚合在 1b 期再关联 after_sales。
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refund_no", sa.String(32), nullable=False, unique=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("transaction_id", sa.String(100), nullable=True, unique=True),
        sa.Column("refund_reason", sa.String(500), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fail_reason", sa.String(500), nullable=True),
        sa.Column("client_request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("payment_id", "client_request_id", name="uq_refunds_payment_request"),
        sa.CheckConstraint("amount_cents >= 0", name="ck_refunds_amount_nonnegative"),
    )
    op.create_index("ix_refunds_payment_id", "refunds", ["payment_id"])
    op.create_index("ix_refunds_status", "refunds", ["status"])


def downgrade() -> None:
    """反向撤销本迁移，恢复 140700 的兼容列。"""
    op.drop_index("ix_refunds_status", table_name="refunds")
    op.drop_index("ix_refunds_payment_id", table_name="refunds")
    op.drop_table("refunds")
    op.drop_index("ix_stock_logs_source", table_name="stock_logs")
    op.drop_index("ix_stock_logs_created_at", table_name="stock_logs")
    for column in ("reason", "operator_id", "change_qty", "change_type", "source_id", "source_type"):
        op.drop_column("stock_logs", column)
    op.drop_constraint("ck_orders_paid_nonnegative", "orders", type_="check")
    op.drop_index("ix_orders_refund_status", table_name="orders")
    # downgrade 同样先移除 JSONB 默认值，避免默认表达式阻止类型回退。
    op.alter_column(
        "orders",
        "address_snapshot",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        server_default=None,
    )
    op.alter_column(
        "orders",
        "address_snapshot",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=sa.Text(),
        existing_nullable=False,
        postgresql_using="address_snapshot::text",
    )
    op.alter_column(
        "orders",
        "address_snapshot",
        existing_type=sa.Text(),
        server_default=sa.text("'{}'"),
    )
    for column in ("cancel_reason", "cancelled_at", "completed_at", "paid_at", "remark", "refund_status"):
        op.drop_column("orders", column)
    op.drop_index("ix_product_spec_values_spec_id", table_name="product_spec_values")
    op.drop_table("product_spec_values")
    op.drop_index("ix_product_specs_product_id", table_name="product_specs")
    op.drop_table("product_specs")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_column("products", "seo_keywords")
    op.drop_column("products", "seo_description")
    op.drop_column("products", "seo_title")
    op.drop_constraint("uq_skus_product_spec_hash", "skus", type_="unique")
    op.drop_index("ix_skus_status", table_name="skus")
    op.drop_index("ix_skus_product_id", table_name="skus")
    op.alter_column("skus", "product_id", new_column_name="spu_id")
    op.create_index("ix_skus_spu_id", "skus", ["spu_id"])
    op.create_unique_constraint("uq_skus_spu_spec_hash", "skus", ["spu_id", "spec_hash"])
