"""创建优惠券和物流轨迹表，并支持三期营销基础能力。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_190000"
down_revision: str | None = "20260906_180000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建优惠券、领取记录和物流轨迹。"""
    op.create_table(
        "coupons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("coupon_type", sa.String(length=20), nullable=False, server_default="FULL_REDUCTION"),
        sa.Column("threshold_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_percent", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claimed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_coupons_code"),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"])
    op.create_index("ix_coupons_enabled", "coupons", ["enabled"])
    op.create_table(
        "coupon_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("coupon_id", sa.Integer(), sa.ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("coupon_id", "user_id", name="uq_coupon_claims_coupon_user"),
    )
    op.create_index("ix_coupon_claims_coupon_id", "coupon_claims", ["coupon_id"])
    op.create_index("ix_coupon_claims_user_id", "coupon_claims", ["user_id"])
    op.create_table(
        "shipment_tracking_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("location", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_shipment_tracking_events_order_id", "shipment_tracking_events", ["order_id"])


def downgrade() -> None:
    """回滚营销和物流基础表。"""
    op.drop_index("ix_shipment_tracking_events_order_id", table_name="shipment_tracking_events")
    op.drop_table("shipment_tracking_events")
    op.drop_index("ix_coupon_claims_user_id", table_name="coupon_claims")
    op.drop_index("ix_coupon_claims_coupon_id", table_name="coupon_claims")
    op.drop_table("coupon_claims")
    op.drop_index("ix_coupons_enabled", table_name="coupons")
    op.drop_index("ix_coupons_code", table_name="coupons")
    op.drop_table("coupons")
