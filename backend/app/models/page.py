"""商城低代码页面模型。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class StorePage(Base):
    """版本化商城页面 Schema。"""

    __tablename__ = "store_pages"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(120), default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    schema: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    is_home: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PageVariant(Base):
    """页面 A/B 变体配置，比例使用百分数整数。"""

    __tablename__ = "page_variants"
    __table_args__ = (
        CheckConstraint("allocation_percent >= 0 AND allocation_percent <= 100", name="ck_page_variant_allocation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("store_pages.id", ondelete="CASCADE"), index=True)
    key: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    allocation_percent: Mapped[int] = mapped_column(Integer, default=0)
    schema: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PageConversionEvent(Base):
    """页面变体转化事件，供后续分析或数据仓库消费。"""

    __tablename__ = "page_conversion_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    page_id: Mapped[int] = mapped_column(ForeignKey("store_pages.id", ondelete="CASCADE"), index=True)
    variant_key: Mapped[str] = mapped_column(String(40), default="control")
    event_name: Mapped[str] = mapped_column(String(80))
    anonymous_id: Mapped[str] = mapped_column(String(100), default="")
    event_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
