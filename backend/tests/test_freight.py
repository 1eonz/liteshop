"""运费模板按地区、重量和件数计费测试。"""

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.freight import FreightTemplate, FreightTemplateItem
from app.repositories.freight import FreightRepository
from app.schemas.freight import FreightTemplateItemCreate, FreightTemplateUpdate
from app.services.freight import FreightLine, FreightService


def _template(template_type: str, item: FreightTemplateItem) -> tuple[FreightTemplate, FreightTemplateItem]:
    """构造不依赖数据库的模板聚合。"""
    template = FreightTemplate(type=template_type, enabled=True, name="测试模板", is_default=True)
    template.items = [item]
    return template, item


def test_weight_freight_rounds_additional_unit_up() -> None:
    """超过首重但不足一续重时按一个续重计费。"""
    template, item = _template(
        "WEIGHT",
        FreightTemplateItem(
            region_codes=["330000"],
            first_unit=Decimal("1.00"),
            first_fee=800,
            additional_unit=Decimal("0.50"),
            additional_fee=300,
            free_condition=None,
        ),
    )
    amount = FreightService.calculate_amount(template, item, [FreightLine(1, 1100, 1000)], 1000)
    assert amount == 1100


def test_piece_freight_supports_free_condition() -> None:
    """满足包邮门槛时不再收取模板费用。"""
    template, item = _template(
        "PIECE",
        FreightTemplateItem(
            region_codes=[],
            first_unit=Decimal("1"),
            first_fee=1000,
            additional_unit=Decimal("1"),
            additional_fee=200,
            free_condition={"min_amount": 9900},
        ),
    )
    amount = FreightService.calculate_amount(template, item, [FreightLine(2, 0, 6000)], 12000)
    assert amount == 0


def test_update_template_replaces_all_items_atomically() -> None:
    """模板基础字段和多个计费项由同一服务事务整体替换。"""
    template, _ = _template(
        "PIECE",
        FreightTemplateItem(
            region_codes=[],
            first_unit=Decimal("1"),
            first_fee=100,
            additional_unit=Decimal("1"),
            additional_fee=50,
            free_condition=None,
        ),
    )
    template.id = 1
    now = datetime.now(UTC)
    template.created_at = now
    template.updated_at = now
    repository = cast(
        FreightRepository,
        type("Repository", (), {"get_template": AsyncMock(return_value=template)})(),
    )
    service = FreightService(repository=repository)
    session = cast(AsyncSession, type("Session", (), {"flush": AsyncMock()})())
    result = asyncio.run(
        service.update_template(
            session,
            1,
            FreightTemplateUpdate(
                name="华东模板",
                items=[
                    FreightTemplateItemCreate.model_validate(
                        {
                            "regionCodes": ["310000"],
                            "firstUnit": 1,
                            "firstFee": 800,
                            "additionalUnit": 1,
                            "additionalFee": 200,
                        }
                    ),
                    FreightTemplateItemCreate.model_validate(
                        {
                            "regionCodes": ["330000"],
                            "firstUnit": 2,
                            "firstFee": 900,
                            "additionalUnit": 1,
                            "additionalFee": 250,
                        }
                    ),
                ],
            ),
        )
    )
    assert result["name"] == "华东模板"
    assert len(template.items) == 2
    assert template.items[1].first_fee == 900
