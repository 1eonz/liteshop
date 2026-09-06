"""创建商城低代码页面表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_140000"
down_revision: str | None = "20260906_130000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建页面 Schema 存储。"""
    op.create_table(
        "store_pages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("schema", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("is_home", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_store_pages_is_home", "store_pages", ["is_home"])


def downgrade() -> None:
    """删除页面 Schema 表。"""
    op.drop_index("ix_store_pages_is_home", table_name="store_pages")
    op.drop_table("store_pages")
