"""增加会员等级、积分和标签字段。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_110000"
down_revision: str | None = "20260906_100000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """建立会员基础字段。"""
    op.add_column("users", sa.Column("member_level", sa.String(length=20), nullable=False, server_default="NORMAL"))
    op.add_column("users", sa.Column("points", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("tags", sa.JSON(), nullable=False, server_default="[]"))
    op.create_index("ix_users_member_level", "users", ["member_level"])


def downgrade() -> None:
    """回滚会员基础字段。"""
    op.drop_index("ix_users_member_level", table_name="users")
    op.drop_column("users", "tags")
    op.drop_column("users", "points")
    op.drop_column("users", "member_level")
