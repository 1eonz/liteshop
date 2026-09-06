"""官网联系表单 API。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors import ApiError
from ..schemas.contact import ContactFormCreate
from ..services.contact import ContactFormError, contact_service
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from .responses import success

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("/forms", status_code=202)
async def create_contact_form(payload: ContactFormCreate, x_request_id: str = Header(...)) -> dict[str, object]:
    """受理官网联系表单，重复请求返回第一次结果。"""

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        result = await contact_service.create(session, payload.model_dump())
        return IdempotentResult(result.as_dict(), "form_submission", str(result.id))

    try:
        result = await idempotency_service.execute(
            user_id="anonymous",
            request_id=x_request_id,
            action_type="contact_form_create",
            operation=operation,
        )
        return success(result)
    except ContactFormError as error:
        raise ApiError(status_code=422, code=42210, i18n_key="contact.invalid_form", message=str(error)) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429, code=42901, i18n_key="common.request_in_progress", message="请求正在处理中，请稍后再试"
        ) from error
