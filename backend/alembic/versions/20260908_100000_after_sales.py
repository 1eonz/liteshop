"""创建售后单与状态字段。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_100000"
down_revision: str | None = "20260907_094000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建订单项售后聚合。"""
    op.create_table(
        "after_sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("after_sale_no", sa.String(length=40), nullable=False),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("evidence_urls", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("return_address", sa.Text(), nullable=False, server_default=""),
        sa.Column("return_tracking_no", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("audit_reason", sa.String(length=500), nullable=True),
        sa.Column("refund_id", sa.Integer(), sa.ForeignKey("refunds.id"), nullable=True),
        sa.Column("client_request_id", sa.String(length=64), nullable=False),
        sa.Column("active_key", sa.String(length=20), nullable=True, server_default="ACTIVE"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("after_sale_no", name="uq_after_sales_no"),
        sa.UniqueConstraint("order_item_id", "active_key", name="uq_after_sales_active_item"),
        sa.UniqueConstraint("user_id", "client_request_id", name="uq_after_sales_user_request"),
        sa.CheckConstraint("amount_cents > 0", name="ck_after_sales_amount_positive"),
    )
    op.create_index("ix_after_sales_status", "after_sales", ["status"])
    op.create_index("ix_after_sales_order_id", "after_sales", ["order_id"])


def downgrade() -> None:
    """删除售后单。"""
    op.drop_index("ix_after_sales_order_id", table_name="after_sales")
    op.drop_index("ix_after_sales_status", table_name="after_sales")
    op.drop_table("after_sales")
