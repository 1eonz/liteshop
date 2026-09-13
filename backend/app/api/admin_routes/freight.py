"""管理后台运费模板路由。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.freight import (
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from ..dependencies import CurrentSubject
from ..responses import success
from .common import admin_service, authorize_read, execute_write, require_database, session_dependency

router = APIRouter()


@router.get("/freight-templates")
async def list_freight_templates(
    subject: CurrentSubject, session: AsyncSession = session_dependency
) -> dict[str, object]:
    """读取后台运费模板列表。"""
    require_database()
    await authorize_read(session, subject, "settings.read")
    return success({"items": await admin_service.list_freight_templates(session)})


@router.post("/freight-templates")
async def create_freight_template(
    payload: FreightTemplateCreate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """创建运费模板。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_freight_template_create",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.create_freight_template(
            session, payload, user_id, request_id
        ),
    )


@router.put("/freight-templates/{template_id}")
async def update_freight_template(
    template_id: int,
    payload: FreightTemplateUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """更新运费模板。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_template_update:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.update_freight_template(
            session, template_id, payload, user_id, request_id
        ),
    )


@router.delete("/freight-templates/{template_id}")
async def delete_freight_template(
    template_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """删除运费模板。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_template_delete:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.delete_freight_template(
            session, template_id, user_id, request_id
        ),
    )


@router.post("/freight-templates/{template_id}/items")
async def add_freight_item(
    template_id: int,
    payload: FreightTemplateItemCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """为模板增加地区计费项。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_create:{template_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.add_freight_item(
            session, template_id, payload, user_id, request_id
        ),
    )


@router.put("/freight-templates/{template_id}/items/{item_id}")
async def update_freight_item(
    template_id: int,
    item_id: int,
    payload: FreightTemplateItemUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """更新地区计费项。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_update:{item_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.update_freight_item(
            session, template_id, item_id, payload, user_id, request_id
        ),
    )


@router.delete("/freight-templates/{template_id}/items/{item_id}")
async def delete_freight_item(
    template_id: int, item_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """删除地区计费项。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_freight_item_delete:{item_id}",
        permission="settings.write",
        resource_type="freight_template",
        operation=lambda session, user_id, request_id: admin_service.delete_freight_item(
            session, template_id, item_id, user_id, request_id
        ),
    )
