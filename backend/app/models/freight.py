"""运费模板与地区计费项模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.database import Base


class FreightTemplate(Base):
    """按重量、件数或地区计算运费的模板。"""

    __tablename__ = "freight_templates"
    __table_args__ = (UniqueConstraint("name", name="uq_freight_templates_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[str] = mapped_column(String(20))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    items: Mapped[list["FreightTemplateItem"]] = relationship(
        back_populates="template", cascade="all, delete-orphan", order_by="FreightTemplateItem.id"
    )


class FreightTemplateItem(Base):
    """运费模板的地区和首续重计费规则。"""

    __tablename__ = "freight_template_items"
    __table_args__ = (
        CheckConstraint("first_unit > 0", name="ck_freight_items_first_unit_positive"),
        CheckConstraint("first_fee >= 0", name="ck_freight_items_first_fee_nonnegative"),
        CheckConstraint("additional_unit > 0", name="ck_freight_items_additional_unit_positive"),
        CheckConstraint("additional_fee >= 0", name="ck_freight_items_additional_fee_nonnegative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("freight_templates.id", ondelete="CASCADE"), index=True)
    region_codes: Mapped[list[str]] = mapped_column(JSONB, default=list)
    first_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    first_fee: Mapped[int] = mapped_column(Integer)
    additional_unit: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    additional_fee: Mapped[int] = mapped_column(Integer)
    free_condition: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    template: Mapped[FreightTemplate] = relationship(back_populates="items")
