"""官网导航菜单模型。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class NavigationItem(Base):
    """可配置的顶部或底部导航项。"""

    __tablename__ = "navigation_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(100))
    href: Mapped[str] = mapped_column(String(500))
    location: Mapped[str] = mapped_column(String(20), default="header", index=True)
    kind: Mapped[str] = mapped_column(String(20), default="internal")
    open_new_tab: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
