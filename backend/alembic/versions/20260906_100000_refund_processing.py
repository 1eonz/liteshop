"""增加退款渠道处理和重试字段。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_100000"
down_revision: str | None = "20260906_090000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """增加退款处理状态所需字段。"""
    op.add_column("refunds", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("refunds", sa.Column("provider_response", sa.JSON(), nullable=False, server_default="{}"))


def downgrade() -> None:
    """回滚退款处理字段。"""
    op.drop_column("refunds", "provider_response")
    op.drop_column("refunds", "attempt_count")
