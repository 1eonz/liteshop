"""为页面渠道建立复合路由唯一约束，兼容已执行旧迁移的数据库。"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260907_093000"
down_revision: str | None = "20260907_090000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """将页面路由唯一性从全局 slug 调整为渠道加 slug。"""
    op.execute("ALTER TABLE store_pages DROP CONSTRAINT IF EXISTS store_pages_slug_key")
    op.execute("ALTER TABLE store_pages DROP CONSTRAINT IF EXISTS uq_store_pages_channel_slug")
    op.execute("ALTER TABLE store_pages ADD CONSTRAINT uq_store_pages_channel_slug UNIQUE (channel, slug)")


def downgrade() -> None:
    """恢复旧版全局 slug 唯一性。"""
    op.execute("ALTER TABLE store_pages DROP CONSTRAINT IF EXISTS uq_store_pages_channel_slug")
    op.execute("ALTER TABLE store_pages ADD CONSTRAINT store_pages_slug_key UNIQUE (slug)")
