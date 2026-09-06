"""扩展商城页面管理、A/B 变体和商品推荐字段。"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260906_180000"
down_revision: str | None = "20260906_170000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """增加页面名称、变体、转化事件与商品标签。"""
    op.add_column("store_pages", sa.Column("name", sa.String(length=120), nullable=False, server_default=""))
    op.add_column(
        "products",
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
    )
    op.add_column(
        "products",
        sa.Column(
            "recommended_product_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )
    op.create_table(
        "page_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("store_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("allocation_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("schema", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("page_id", "key", name="uq_page_variants_page_key"),
        sa.CheckConstraint("allocation_percent >= 0 AND allocation_percent <= 100", name="ck_page_variant_allocation"),
    )
    op.create_index("ix_page_variants_page_id", "page_variants", ["page_id"])
    op.create_index("ix_page_variants_enabled", "page_variants", ["enabled"])
    op.create_table(
        "page_conversion_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("page_id", sa.Integer(), sa.ForeignKey("store_pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_key", sa.String(length=40), nullable=False, server_default="control"),
        sa.Column("event_name", sa.String(length=80), nullable=False),
        sa.Column("anonymous_id", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_page_conversion_events_page_id", "page_conversion_events", ["page_id"])


def downgrade() -> None:
    """回滚页面扩展。"""
    op.drop_index("ix_page_conversion_events_page_id", table_name="page_conversion_events")
    op.drop_table("page_conversion_events")
    op.drop_index("ix_page_variants_enabled", table_name="page_variants")
    op.drop_index("ix_page_variants_page_id", table_name="page_variants")
    op.drop_table("page_variants")
    op.drop_column("products", "recommended_product_ids")
    op.drop_column("products", "tags")
    op.drop_column("store_pages", "name")
