"""官网联系表单仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.form_submission import FormSubmission


class ContactRepository:
    """封装联系表单的持久化细节。"""

    async def create(
        self,
        session: AsyncSession,
        *,
        name: str,
        email: str,
        phone: str,
        company: str,
        message: str,
    ) -> FormSubmission:
        """创建待处理的联系表单。"""
        now = datetime.now(UTC)
        submission = FormSubmission(
            name=name,
            email=email,
            phone=phone,
            company=company,
            message=message,
            custom_fields={},
            source="site",
            status="NEW",
            created_at=now,
            updated_at=now,
        )
        session.add(submission)
        await session.flush()
        return submission

    async def get(self, session: AsyncSession, submission_id: int) -> FormSubmission | None:
        """按 ID 读取联系表单。"""
        return cast(
            FormSubmission | None,
            await session.scalar(select(FormSubmission).where(FormSubmission.id == submission_id)),
        )
