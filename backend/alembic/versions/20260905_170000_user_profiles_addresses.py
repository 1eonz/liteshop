"""补充用户资料字段和收货地址表。"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260905_170000"
down_revision: str | None = "20260905_140700"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """扩展用户资料并创建收货地址表。"""
    op.add_column("users", sa.Column("nickname", sa.String(50), nullable=False, server_default=""))
    op.add_column("users", sa.Column("avatar", sa.String(500), nullable=False, server_default=""))
    op.add_column("users", sa.Column("gender", sa.String(10), nullable=False, server_default="UNKNOWN"))
    op.add_column("users", sa.Column("birthday", sa.Date(), nullable=True))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")
        ),
    )
    op.create_table(
        "addresses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("receiver_name", sa.String(50), nullable=False),
        sa.Column("phone", sa.String(20), nullable=False),
        sa.Column("province_code", sa.String(20), nullable=False),
        sa.Column("city_code", sa.String(20), nullable=False),
        sa.Column("district_code", sa.String(20), nullable=False),
        sa.Column("detail", sa.String(500), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_addresses_user_id", "addresses", ["user_id"])
    op.create_index(
        "uq_addresses_one_default_per_user",
        "addresses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )


def downgrade() -> None:
    """移除地址表和用户扩展字段。"""
    op.drop_index("uq_addresses_one_default_per_user", table_name="addresses")
    op.drop_index("ix_addresses_user_id", table_name="addresses")
    op.drop_table("addresses")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "birthday")
    op.drop_column("users", "gender")
    op.drop_column("users", "avatar")
    op.drop_column("users", "nickname")
