"""创建运费模板和地区计费项。"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260905_190000"
down_revision: str | None = "20260905_180000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """建立按地区、重量和件数计费的运费模板表。"""
    op.create_table(
        "freight_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", name="uq_freight_templates_name"),
        sa.CheckConstraint("type IN ('WEIGHT', 'PIECE', 'REGION')", name="ck_freight_templates_type"),
    )
    op.create_index("ix_freight_templates_is_default", "freight_templates", ["is_default"])
    op.create_index("ix_freight_templates_enabled", "freight_templates", ["enabled"])
    op.create_index(
        "uq_freight_templates_one_default",
        "freight_templates",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )
    op.create_table(
        "freight_template_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("freight_templates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("region_codes", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("first_unit", sa.Numeric(10, 2), nullable=False),
        sa.Column("first_fee", sa.Integer(), nullable=False),
        sa.Column("additional_unit", sa.Numeric(10, 2), nullable=False),
        sa.Column("additional_fee", sa.Integer(), nullable=False),
        sa.Column("free_condition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("first_unit > 0", name="ck_freight_items_first_unit_positive"),
        sa.CheckConstraint("first_fee >= 0", name="ck_freight_items_first_fee_nonnegative"),
        sa.CheckConstraint("additional_unit > 0", name="ck_freight_items_additional_unit_positive"),
        sa.CheckConstraint("additional_fee >= 0", name="ck_freight_items_additional_fee_nonnegative"),
    )
    op.create_index("ix_freight_template_items_template_id", "freight_template_items", ["template_id"])


def downgrade() -> None:
    """按外键依赖删除运费模板表。"""
    op.drop_index("ix_freight_template_items_template_id", table_name="freight_template_items")
    op.drop_table("freight_template_items")
    op.drop_index("uq_freight_templates_one_default", table_name="freight_templates")
    op.drop_index("ix_freight_templates_enabled", table_name="freight_templates")
    op.drop_index("ix_freight_templates_is_default", table_name="freight_templates")
    op.drop_table("freight_templates")
