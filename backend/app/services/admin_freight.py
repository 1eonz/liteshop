"""管理后台运费模板领域服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.freight import (
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)
from .admin_core import AdminServiceCore


class AdminFreightService(AdminServiceCore):
    """编排运费模板写操作与后台审计。"""

    async def list_freight_templates(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取后台运费模板。"""
        return await self.freight.list_templates(session)

    async def create_freight_template(
        self, session: AsyncSession, payload: FreightTemplateCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建运费模板并记录操作日志。"""
        response = await self.freight.create_template(session, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=int(str(response["id"])),
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_freight_template(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新运费模板并记录操作日志。"""
        response = await self.freight.update_template(session, template_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_freight_template(
        self, session: AsyncSession, template_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除运费模板并记录操作日志。"""
        response = await self.freight.delete_template(session, template_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def add_freight_item(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateItemCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """增加运费模板计费项并记录操作日志。"""
        response = await self.freight.add_item(session, template_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_freight_item(
        self,
        session: AsyncSession,
        template_id: int,
        item_id: int,
        payload: FreightTemplateItemUpdate,
        user_id: str,
        request_id: str,
    ) -> dict[str, object]:
        """更新运费模板计费项并记录操作日志。"""
        response = await self.freight.update_item(session, template_id, item_id, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_freight_item(
        self, session: AsyncSession, template_id: int, item_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除运费模板计费项并记录操作日志。"""
        response = await self.freight.delete_item(session, template_id, item_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="FREIGHT_TEMPLATE",
            resource_id=template_id,
            action="ITEM_DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response
