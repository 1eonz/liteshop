"""创建 LiteShop 基础商品、用户与审计表。"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """创建商品、SKU、用户、RBAC 和审计基础表。"""
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("icon", sa.String(500), nullable=False, server_default=""),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id"), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("subtitle", sa.String(200), nullable=False, server_default=""),
        sa.Column("brand", sa.String(100), nullable=False, server_default=""),
        sa.Column("main_images", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("detail_images", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("detail_html", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sales_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_products_status", "products", ["status"])
    op.create_table(
        "skus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("spu_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("spec_values", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("spec_hash", sa.String(64), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=False),
        sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("physical_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("image", sa.String(500), nullable=False, server_default=""),
        sa.Column("bar_code", sa.String(50), nullable=False, server_default=""),
        sa.Column("safety_stock", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("spu_id", "spec_hash", name="uq_skus_spu_spec_hash"),
        sa.CheckConstraint("price_cents >= 0", name="ck_skus_price_nonnegative"),
        sa.CheckConstraint("physical_stock >= 0", name="ck_skus_physical_nonnegative"),
        sa.CheckConstraint("locked_stock >= 0", name="ck_skus_locked_nonnegative"),
        sa.CheckConstraint("locked_stock <= physical_stock", name="ck_skus_stock_layers_consistent"),
    )
    op.create_index("ix_skus_spu_id", "skus", ["spu_id"])
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(32), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False, unique=True),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(128), nullable=False, unique=True),
    )
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
    )
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id"), primary_key=True),
    )
    op.create_table(
        "operation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("before_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("after_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(45), nullable=False, server_default=""),
        sa.Column("user_agent", sa.Text(), nullable=False, server_default=""),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_operation_logs_admin_id", "operation_logs", ["admin_id"])
    op.create_index("ix_operation_logs_resource", "operation_logs", ["resource_type", "resource_id"])
    op.create_index("ix_operation_logs_request_id", "operation_logs", ["request_id"])
    op.create_index("ix_operation_logs_created_at", "operation_logs", ["created_at"])


def downgrade() -> None:
    """按外键依赖顺序回滚基础表。"""
    op.drop_index("ix_operation_logs_created_at", table_name="operation_logs")
    op.drop_index("ix_operation_logs_request_id", table_name="operation_logs")
    op.drop_index("ix_operation_logs_resource", table_name="operation_logs")
    op.drop_index("ix_operation_logs_admin_id", table_name="operation_logs")
    op.drop_table("operation_logs")
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_index("ix_skus_spu_id", table_name="skus")
    op.drop_table("skus")
    op.drop_index("ix_products_status", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")
