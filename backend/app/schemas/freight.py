"""运费模板与运费计算 DTO。"""

from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field

FreightType = Literal["WEIGHT", "PIECE", "REGION"]


class FreightTemplateItemCreate(BaseModel):
    """创建地区计费项，金额使用整数分，重量单位为千克。"""

    region_codes: list[str] = Field(default_factory=list, alias="regionCodes")
    first_unit: Annotated[Decimal, Field(alias="firstUnit", gt=0, max_digits=10, decimal_places=2)]
    first_fee: Annotated[int, Field(alias="firstFee", ge=0)]
    additional_unit: Annotated[Decimal, Field(alias="additionalUnit", gt=0, max_digits=10, decimal_places=2)]
    additional_fee: Annotated[int, Field(alias="additionalFee", ge=0)]
    free_condition: dict[str, object] | None = Field(default=None, alias="freeCondition")
    model_config = {"populate_by_name": True}


class FreightTemplateItemUpdate(BaseModel):
    """更新地区计费项。"""

    region_codes: list[str] | None = Field(default=None, alias="regionCodes")
    first_unit: Decimal | None = Field(default=None, alias="firstUnit", gt=0, max_digits=10, decimal_places=2)
    first_fee: int | None = Field(default=None, alias="firstFee", ge=0)
    additional_unit: Decimal | None = Field(default=None, alias="additionalUnit", gt=0, max_digits=10, decimal_places=2)
    additional_fee: int | None = Field(default=None, alias="additionalFee", ge=0)
    free_condition: dict[str, object] | None = Field(default=None, alias="freeCondition")
    model_config = {"populate_by_name": True}


class FreightTemplateCreate(BaseModel):
    """创建运费模板。"""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    type: FreightType
    is_default: bool = Field(default=False, alias="isDefault")
    enabled: bool = True
    items: list[FreightTemplateItemCreate] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


class FreightTemplateUpdate(BaseModel):
    """更新运费模板基础信息。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: FreightType | None = None
    is_default: bool | None = Field(default=None, alias="isDefault")
    enabled: bool | None = None
    items: list[FreightTemplateItemCreate] | None = Field(default=None, min_length=1, max_length=100)
    model_config = {"populate_by_name": True}


class FreightLineInput(BaseModel):
    """运费计算商品行。"""

    sku_id: Annotated[int, Field(alias="skuId", gt=0)]
    quantity: Annotated[int, Field(gt=0, le=999)]
    model_config = {"populate_by_name": True}


class FreightCalculateRequest(BaseModel):
    """按收货省份和 SKU 实时计算运费。"""

    items: Annotated[list[FreightLineInput], Field(min_length=1)]
    province_code: Annotated[str, Field(alias="provinceCode", min_length=1, max_length=20)]
    product_amount: Annotated[int, Field(alias="productAmount", ge=0)]
    template_id: int | None = Field(default=None, alias="templateId", gt=0)
    model_config = {"populate_by_name": True}
