"""官网联系表单领域服务。"""

from collections.abc import Mapping
from dataclasses import dataclass
from email.utils import parseaddr

from sqlalchemy.ext.asyncio import AsyncSession

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


contact_service = ContactService()
