"""运费模板计费领域服务。"""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_UP, Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.freight import FreightTemplate, FreightTemplateItem
from ..repositories.freight import FreightRepository
from ..repositories.product import ProductRepository
from ..schemas.freight import (
    FreightCalculateRequest,
    FreightTemplateCreate,
    FreightTemplateItemCreate,
    FreightTemplateItemUpdate,
    FreightTemplateUpdate,
)


class FreightError(ValueError):
    """运费模板或计算参数不合法。"""


@dataclass(frozen=True)
class FreightLine:
    """参与运费计算的服务器端商品快照。"""

    quantity: int
    weight_grams: int
    price_cents: int


class FreightService:
    """读取模板并按地区、重量或件数计算整数分运费。"""

    def __init__(
        self,
        repository: FreightRepository | None = None,
        products: ProductRepository | None = None,
    ) -> None:
        self.repository = repository or FreightRepository()
        self.products = products or ProductRepository()

    @staticmethod
    def _find_item(template: FreightTemplate, province_code: str) -> FreightTemplateItem | None:
        """按省级编码匹配地区项，空地区项作为全国兜底。"""
        fallback: FreightTemplateItem | None = None
        for item in template.items:
            if not item.region_codes:
                fallback = item
            elif province_code in item.region_codes:
                return item
        return fallback

    @staticmethod
    def calculate_amount(
        template: FreightTemplate | None,
        item: FreightTemplateItem | None,
        lines: list[FreightLine],
        product_amount: int,
    ) -> int:
        """使用已加载模板计算运费，续重和续件按不足一单位向上取整。"""
        if template is None or not template.enabled or item is None:
            return 0
        if item.free_condition:
            minimum = item.free_condition.get("min_amount", item.free_condition.get("minAmount", 0))
            minimum_cents = int(str(minimum or 0))
            if minimum_cents > 0 and product_amount >= minimum_cents:
                return 0
        if template.type == "WEIGHT":
            total_weight = Decimal(sum(line.weight_grams * line.quantity for line in lines)) / Decimal(1000)
            if total_weight <= item.first_unit:
                return item.first_fee
            extra_units = ((total_weight - item.first_unit) / item.additional_unit).quantize(
                Decimal("1"), rounding=ROUND_UP
            )
            return item.first_fee + int(extra_units) * item.additional_fee
        if template.type == "PIECE":
            total_quantity = sum(line.quantity for line in lines)
            if Decimal(total_quantity) <= item.first_unit:
                return item.first_fee
            extra_units = ((Decimal(total_quantity) - item.first_unit) / item.additional_unit).quantize(
                Decimal("1"), rounding=ROUND_UP
            )
            return item.first_fee + int(extra_units) * item.additional_fee
        return item.first_fee

    async def calculate(
        self,
        session: AsyncSession,
        payload: FreightCalculateRequest,
        *,
        template_id: int | None = None,
    ) -> int:
        """实时读取 SKU 重量和价格，禁止信任客户端商品重量。"""
        sku_ids = [item.sku_id for item in payload.items]
        if len(sku_ids) != len(set(sku_ids)):
            raise FreightError("运费计算商品不能重复")
        lines: list[FreightLine] = []
        actual_amount = 0
        for item in payload.items:
            sku = await self.products.get_sku(session, item.sku_id)
            if sku is None or sku.status != "ACTIVE" or sku.spu.status != "ON_SHELF":
                raise FreightError("商品已下架或 SKU 不存在")
            lines.append(
                FreightLine(
                    quantity=item.quantity,
                    weight_grams=sku.weight_grams or 0,
                    price_cents=sku.price_cents,
                )
            )
            actual_amount += sku.price_cents * item.quantity
        if actual_amount != payload.product_amount:
            raise FreightError("商品金额已变更")
        return await self.calculate_lines(
            session,
            lines,
            payload.province_code,
            actual_amount,
            template_id=template_id,
        )

    async def calculate_lines(
        self,
        session: AsyncSession,
        lines: list[FreightLine],
        province_code: str,
        product_amount: int,
        *,
        template_id: int | None = None,
    ) -> int:
        """使用已由订单工作流锁定的 SKU 快照计算运费。"""
        template = (
            await self.repository.get_template(session, template_id)
            if template_id is not None
            else await self.repository.get_default_template(session)
        )
        if template_id is not None and (template is None or not template.enabled):
            raise FreightError("运费模板不存在或未启用")
        item = self._find_item(template, province_code) if template else None
        return self.calculate_amount(template, item, lines, product_amount)

    @staticmethod
    def template_response(template: FreightTemplate) -> dict[str, object]:
        """转换模板和计费项为 API 数据。"""
        return {
            "id": template.id,
            "name": template.name,
            "type": template.type,
            "isDefault": template.is_default,
            "enabled": template.enabled,
            "items": [
                {
                    "id": item.id,
                    "regionCodes": item.region_codes,
                    "firstUnit": str(item.first_unit),
                    "firstFee": item.first_fee,
                    "additionalUnit": str(item.additional_unit),
                    "additionalFee": item.additional_fee,
                    "freeCondition": item.free_condition,
                }
                for item in template.items
            ],
            "createdAt": template.created_at.isoformat(),
            "updatedAt": template.updated_at.isoformat(),
        }

    async def list_templates(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取全部运费模板。"""
        return [self.template_response(template) for template in await self.repository.list_templates(session)]

    async def create_template(self, session: AsyncSession, payload: FreightTemplateCreate) -> dict[str, object]:
        """创建模板并按需设置默认模板。"""
        now = datetime.now(UTC)
        if payload.is_default:
            await self.repository.clear_default(session)
        template = FreightTemplate(
            name=payload.name,
            type=payload.type,
            is_default=payload.is_default,
            enabled=payload.enabled,
            created_at=now,
            updated_at=now,
        )
        template.items = [
            FreightTemplateItem(
                region_codes=item.region_codes,
                first_unit=item.first_unit,
                first_fee=item.first_fee,
                additional_unit=item.additional_unit,
                additional_fee=item.additional_fee,
                free_condition=item.free_condition,
                created_at=now,
                updated_at=now,
            )
            for item in payload.items
        ]
        await self.repository.add_template(session, template)
        return self.template_response(template)

    async def update_template(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateUpdate
    ) -> dict[str, object]:
        """更新模板基础字段。"""
        template = await self.repository.get_template(session, template_id, for_update=True)
        if template is None:
            raise FreightError("运费模板不存在")
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        if changes.get("is_default") is True:
            await self.repository.clear_default(session, except_id=template_id)
        for field, value in changes.items():
            setattr(template, field, value)
        template.updated_at = datetime.now(UTC)
        await session.flush()
        return self.template_response(template)

    async def delete_template(self, session: AsyncSession, template_id: int) -> dict[str, object]:
        """删除模板及其计费项。"""
        template = await self.repository.get_template(session, template_id, for_update=True)
        if template is None:
            raise FreightError("运费模板不存在")
        await session.delete(template)
        await session.flush()
        return {"deleted": True, "templateId": template_id}

    async def add_item(
        self, session: AsyncSession, template_id: int, payload: FreightTemplateItemCreate
    ) -> dict[str, object]:
        """为模板增加地区计费项。"""
        template = await self.repository.get_template(session, template_id, for_update=True)
        if template is None:
            raise FreightError("运费模板不存在")
        item = FreightTemplateItem(
            template=template,
            region_codes=payload.region_codes,
            first_unit=payload.first_unit,
            first_fee=payload.first_fee,
            additional_unit=payload.additional_unit,
            additional_fee=payload.additional_fee,
            free_condition=payload.free_condition,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        await self.repository.add_item(session, item)
        # 模板由 selectinload 预加载，显式维护集合才能在同一事务返回最新计费项。
        if item not in template.items:
            template.items.append(item)
        return self.template_response(template)

    async def update_item(
        self,
        session: AsyncSession,
        template_id: int,
        item_id: int,
        payload: FreightTemplateItemUpdate,
    ) -> dict[str, object]:
        """更新模板计费项。"""
        item = await self.repository.get_item(session, template_id, item_id)
        if item is None:
            raise FreightError("运费计费项不存在")
        for field, value in payload.model_dump(exclude_unset=True, by_alias=False).items():
            setattr(item, field, value)
        item.updated_at = datetime.now(UTC)
        await session.flush()
        template = await self.repository.get_template(session, template_id)
        if template is None:
            raise FreightError("运费模板不存在")
        return self.template_response(template)

    async def delete_item(self, session: AsyncSession, template_id: int, item_id: int) -> dict[str, object]:
        """删除模板计费项。"""
        item = await self.repository.get_item(session, template_id, item_id)
        if item is None:
            raise FreightError("运费计费项不存在")
        await self.repository.delete_item(session, item)
        return {"deleted": True, "templateId": template_id, "itemId": item_id}


freight_service = FreightService()
