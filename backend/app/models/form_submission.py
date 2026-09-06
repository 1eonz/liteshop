"""官网联系表单提交模型。"""

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class FormSubmission(Base):
    """保存官网联系表单，状态用于后台处理流转。"""

    __tablename__ = "form_submissions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(320))
    phone: Mapped[str] = mapped_column(String(30), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text)
    custom_fields: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(40), default="site")
    status: Mapped[str] = mapped_column(String(20), default="NEW", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
