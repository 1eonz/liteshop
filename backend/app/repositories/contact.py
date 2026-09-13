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

    async def get_for_update(self, session: AsyncSession, submission_id: int) -> FormSubmission | None:
        """锁定一条联系表单，供后台状态流转使用。"""
        return cast(FormSubmission | None, await session.get(FormSubmission, submission_id, with_for_update=True))

    async def flush(self, session: AsyncSession) -> None:
        """刷新联系表单字段变更，不提交外层事务。"""
        await session.flush()

    async def list(self, session: AsyncSession, *, status: str | None = None, limit: int = 100) -> list[FormSubmission]:
        """按创建时间倒序读取联系表单。"""
        statement = select(FormSubmission).order_by(FormSubmission.created_at.desc(), FormSubmission.id.desc())
        if status is not None:
            statement = statement.where(FormSubmission.status == status)
        result = await session.scalars(statement.limit(limit))
        return list(result.all())
