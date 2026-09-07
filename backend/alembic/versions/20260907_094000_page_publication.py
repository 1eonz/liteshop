"""增加页面草稿与发布状态。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_094000"
down_revision: str | None = "20260907_093000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """保留历史页面公开状态，新建页面由应用默认创建为草稿。"""
    op.add_column("store_pages", sa.Column("status", sa.String(length=20), nullable=False, server_default="PUBLISHED"))
    op.add_column("store_pages", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_store_pages_status", "store_pages", ["status"])


def downgrade() -> None:
    """删除页面发布状态字段。"""
    op.drop_index("ix_store_pages_status", table_name="store_pages")
    op.drop_column("store_pages", "published_at")
    op.drop_column("store_pages", "status")
