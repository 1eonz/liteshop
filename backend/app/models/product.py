"""商品、SKU 与三层库存 ORM 模型。"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class Category(Base):
    """商品分类树节点。"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    icon: Mapped[str] = mapped_column(String(500), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Spu(Base):
    """商品 SPU，名称和主图是商品级快照来源。"""

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(200))
    subtitle: Mapped[str] = mapped_column(String(200), default="")
    brand: Mapped[str] = mapped_column(String(100), default="")
    main_images: Mapped[list[dict[str, object]]] = mapped_column(JSONB, default=list)
    detail_images: Mapped[list[str]] = mapped_column(JSONB, default=list)
    description: Mapped[str] = mapped_column(Text, default="")
    detail_html: Mapped[str] = mapped_column(Text, default="")
    seo_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seo_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    seo_keywords: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    skus: Mapped[list["Sku"]] = relationship(back_populates="spu", cascade="all, delete-orphan")
    specs: Mapped[list["ProductSpec"]] = relationship(back_populates="product", cascade="all, delete-orphan")


class ProductSpec(Base):
    """SPU 的规格定义，例如颜色、尺寸。"""

    __tablename__ = "product_specs"
    __table_args__ = (UniqueConstraint("product_id", "name", name="uq_product_specs_product_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    product: Mapped[Spu] = relationship(back_populates="specs")
    values: Mapped[list["ProductSpecValue"]] = relationship(
        back_populates="spec", cascade="all, delete-orphan", order_by="ProductSpecValue.sort_order"
    )


class ProductSpecValue(Base):
    """规格定义下的可选值，例如颜色的红、蓝。"""

    __tablename__ = "product_spec_values"
    __table_args__ = (UniqueConstraint("spec_id", "value", name="uq_product_spec_values_spec_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    spec_id: Mapped[int] = mapped_column(ForeignKey("product_specs.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    spec: Mapped[ProductSpec] = relationship(back_populates="values")


class Sku(Base):
    """SKU 三层库存：实物库存、锁定库存和计算得到的可售库存。"""

    __tablename__ = "skus"
    __table_args__ = (
        UniqueConstraint("product_id", "spec_hash", name="uq_skus_product_spec_hash"),
        CheckConstraint("price_cents >= 0", name="ck_skus_price_nonnegative"),
        CheckConstraint("physical_stock >= 0", name="ck_skus_physical_nonnegative"),
        CheckConstraint("locked_stock >= 0", name="ck_skus_locked_nonnegative"),
        CheckConstraint("locked_stock <= physical_stock", name="ck_skus_stock_layers_consistent"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    spec_values: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    spec_hash: Mapped[str] = mapped_column(String(64))
    price_cents: Mapped[int] = mapped_column(Integer)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)
    physical_stock: Mapped[int] = mapped_column(Integer, default=0)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)
    weight_grams: Mapped[int | None] = mapped_column(Integer, nullable=True)
    image: Mapped[str] = mapped_column(String(500), default="")
    bar_code: Mapped[str] = mapped_column(String(50), default="")
    safety_stock: Mapped[int] = mapped_column(Integer, default=10)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    spu: Mapped[Spu] = relationship(back_populates="skus")

    @property
    def available_stock(self) -> int:
        """按附录 E3.1 计算可售库存，避免冗余字段漂移。"""
        return self.physical_stock - self.locked_stock
