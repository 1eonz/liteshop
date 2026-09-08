"""增加评价商家回复字段。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260908_110000"
down_revision: str | None = "20260908_100000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """为评价增加回复内容和回复时间。"""
    op.add_column("product_reviews", sa.Column("merchant_reply", sa.Text(), nullable=True))
    op.add_column(
        "product_reviews",
        sa.Column("merchant_replied_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """回滚评价回复字段。"""
    op.drop_column("product_reviews", "merchant_replied_at")
    op.drop_column("product_reviews", "merchant_reply")
