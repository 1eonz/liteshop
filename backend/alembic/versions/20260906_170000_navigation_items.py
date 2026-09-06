"""创建官网导航菜单表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_170000"
down_revision: str | None = "20260906_160000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建顶部和底部导航配置。"""
    op.create_table(
        "navigation_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("href", sa.String(length=500), nullable=False),
        sa.Column("location", sa.String(length=20), nullable=False, server_default="header"),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="internal"),
        sa.Column("open_new_tab", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_navigation_items_location", "navigation_items", ["location"])
    op.create_index("ix_navigation_items_enabled", "navigation_items", ["enabled"])


def downgrade() -> None:
    """删除官网导航配置。"""
    op.drop_index("ix_navigation_items_enabled", table_name="navigation_items")
    op.drop_index("ix_navigation_items_location", table_name="navigation_items")
    op.drop_table("navigation_items")
