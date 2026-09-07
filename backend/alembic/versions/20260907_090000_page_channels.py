"""为低代码页面增加商城/官网渠道标记。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260907_090000"
down_revision: str | None = "20260906_190000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """增加渠道字段并将历史页面标记为商城页。"""
    op.add_column("store_pages", sa.Column("channel", sa.String(length=20), nullable=False, server_default="store"))
    # 历史表由 slug 单列唯一约束创建，渠道隔离后改为复合唯一约束。
    op.drop_constraint("store_pages_slug_key", "store_pages", type_="unique")
    op.create_unique_constraint("uq_store_pages_channel_slug", "store_pages", ["channel", "slug"])
    op.create_index("ix_store_pages_channel", "store_pages", ["channel"])


def downgrade() -> None:
    """回滚页面渠道字段。"""
    op.drop_index("ix_store_pages_channel", table_name="store_pages")
    op.execute("ALTER TABLE store_pages DROP CONSTRAINT IF EXISTS uq_store_pages_channel_slug")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'store_pages_slug_key' AND conrelid = 'store_pages'::regclass
            ) THEN
                ALTER TABLE store_pages ADD CONSTRAINT store_pages_slug_key UNIQUE (slug);
            END IF;
        END $$;
        """
    )
    op.drop_column("store_pages", "channel")
