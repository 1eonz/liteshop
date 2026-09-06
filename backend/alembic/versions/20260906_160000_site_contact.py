"""创建官网联系表单表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260906_160000"
down_revision: str | None = "20260906_150000"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建联系表单持久化表。"""
    op.create_table(
        "form_submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("company", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("custom_fields", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="site"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_form_submissions_status", "form_submissions", ["status"])
    op.create_index("ix_form_submissions_created_at", "form_submissions", ["created_at"])


def downgrade() -> None:
    """删除联系表单持久化表。"""
    op.drop_index("ix_form_submissions_created_at", table_name="form_submissions")
    op.drop_index("ix_form_submissions_status", table_name="form_submissions")
    op.drop_table("form_submissions")
