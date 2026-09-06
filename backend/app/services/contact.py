"""官网联系表单领域服务。"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.form_submission import FormSubmission
from ..repositories.contact import ContactRepository


class ContactFormError(ValueError):
    """联系表单内容不合法。"""


@dataclass(frozen=True)
class ContactResult:
    """联系表单受理结果。"""

    id: int
    status: str

    def as_dict(self) -> dict[str, object]:
        return {"id": self.id, "status": self.status, "accepted": True}


class ContactService:
    """校验联系表单并编排仓储。"""

    def __init__(self, repository: ContactRepository | None = None) -> None:
        self.repository = repository or ContactRepository()
        self._memory: list[ContactResult] = []

    @staticmethod
    def validate(values: Mapping[str, str]) -> None:
        """执行反垃圾与字段校验，网站蜜罐字段必须为空。"""
        if values.get("website", ""):
            raise ContactFormError("表单校验失败")
        if not values.get("name", "").strip() or not values.get("message", "").strip():
            raise ContactFormError("姓名和留言不能为空")
        address = parseaddr(values.get("email", ""))[1]
        if not address or "@" not in address:
            raise ContactFormError("邮箱格式不正确")

    async def create(self, session: AsyncSession | None, values: Mapping[str, str]) -> ContactResult:
        """创建联系表单，数据库模式不在此提交事务。"""
        self.validate(values)
        if session is None:
            result = ContactResult(id=len(self._memory) + 1, status="NEW")
            self._memory.append(result)
            return result
        submission = await self.repository.create(
            session,
            name=values["name"].strip(),
            email=values["email"].strip(),
            phone=values.get("phone", "").strip(),
            company=values.get("company", "").strip(),
            message=values["message"].strip(),
        )
        return ContactResult(id=submission.id, status=submission.status)

    @staticmethod
    def _summary(submission: FormSubmission) -> dict[str, object]:
        """将联系表单转换为后台安全摘要。"""
        item = submission
        return {
            "id": item.id,
            "name": item.name,
            "email": item.email,
            "phone": item.phone,
            "company": item.company,
            "message": item.message,
            "status": item.status,
            "source": item.source,
            "createdAt": item.created_at.isoformat(),
            "updatedAt": item.updated_at.isoformat(),
        }

    async def list_submissions(self, session: AsyncSession, status: str | None = None) -> list[dict[str, object]]:
        """读取后台联系表单列表。"""
        return [self._summary(item) for item in await self.repository.list(session, status=status)]

    async def update_status(self, session: AsyncSession, submission_id: int, status: str) -> dict[str, object]:
        """更新联系表单处理状态。"""
        submission = await self.repository.get_for_update(session, submission_id)
        if submission is None:
            raise ContactFormError("联系表单不存在")
        submission.status = status
        submission.updated_at = datetime.now(UTC)
        await session.flush()
        return self._summary(submission)


contact_service = ContactService()
