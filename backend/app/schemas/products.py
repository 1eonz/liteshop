"""商品与库存 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field, field_validator


class CategoryCreate(BaseModel):
    """创建商品分类。"""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    parent_id: int | None = Field(default=None, alias="parentId")
    icon: str = Field(default="", max_length=500)
    sort_order: int = Field(default=0, alias="sortOrder")
    model_config = {"populate_by_name": True}


class CategoryUpdate(BaseModel):
    """更新商品分类。"""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, alias="parentId")
    icon: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, alias="sortOrder")
    is_active: bool | None = Field(default=None, alias="isActive")
    model_config = {"populate_by_name": True}


class SkuCreate(BaseModel):
    """创建 SKU，库存数量和金额均使用整数。"""

    code: Annotated[str, Field(min_length=1, max_length=50)]
    name: Annotated[str, Field(min_length=1, max_length=160)]
    price_cents: Annotated[int, Field(alias="priceCents", ge=0)]
    cost_cents: Annotated[int, Field(alias="costCents", ge=0)] = 0
    physical_stock: Annotated[int, Field(alias="physicalStock", ge=0)] = 0
    safety_stock: Annotated[int, Field(alias="safetyStock", ge=0)] = 10
    weight_grams: Annotated[int | None, Field(alias="weightGrams", ge=0)] = None
    image: str = Field(default="", max_length=500)
    bar_code: str = Field(default="", alias="barCode", max_length=50)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|DISABLED)$")
    sort_order: int = Field(default=0, alias="sortOrder")
    specs: dict[str, str] = Field(default_factory=dict)
    model_config = {"populate_by_name": True}


class ProductCreate(BaseModel):
    """创建包含 SKU 的商品 SPU。"""

    category_id: int | None = Field(default=None, alias="categoryId")
    name: Annotated[str, Field(min_length=1, max_length=200)]
    subtitle: str = Field(default="", max_length=200)
    brand: str = Field(default="", max_length=100)
    main_images: list[dict[str, object]] = Field(default_factory=list, alias="mainImages")
    detail_images: list[str] = Field(default_factory=list, alias="detailImages")
    detail_html: str = Field(default="", alias="detailHtml")
    seo_title: str | None = Field(default=None, alias="seoTitle", max_length=200)
    seo_description: str | None = Field(default=None, alias="seoDescription", max_length=500)
    seo_keywords: str | None = Field(default=None, alias="seoKeywords", max_length=200)
    specs: list["ProductSpecCreate"] = Field(default_factory=list, alias="specDefinitions")
    description: str = ""
    status: str = Field(default="DRAFT", pattern="^(DRAFT|ON_SHELF|OFF_SHELF)$")
    skus: Annotated[list[SkuCreate], Field(min_length=1)]
    model_config = {"populate_by_name": True}


class ProductUpdate(BaseModel):
    """更新商品 SPU 基础字段。"""

    category_id: int | None = Field(default=None, alias="categoryId")
    name: Annotated[str | None, Field(default=None, min_length=1, max_length=200)]
    subtitle: str | None = Field(default=None, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    main_images: list[dict[str, object]] | None = Field(default=None, alias="mainImages")
    detail_images: list[str] | None = Field(default=None, alias="detailImages")
    detail_html: str | None = Field(default=None, alias="detailHtml")
    seo_title: str | None = Field(default=None, alias="seoTitle", max_length=200)
    seo_description: str | None = Field(default=None, alias="seoDescription", max_length=500)
    seo_keywords: str | None = Field(default=None, alias="seoKeywords", max_length=200)
    description: str | None = None
    status: str | None = Field(default=None, pattern="^(DRAFT|ON_SHELF|OFF_SHELF)$")
    model_config = {"populate_by_name": True}


class ProductSpecValueCreate(BaseModel):
    """创建规格值。"""

    value: Annotated[str, Field(min_length=1, max_length=100)]
    sort_order: int = Field(default=0, alias="sortOrder")
    model_config = {"populate_by_name": True}


class ProductSpecCreate(BaseModel):
    """创建规格定义及其可选值。"""

    name: Annotated[str, Field(min_length=1, max_length=50)]
    sort_order: int = Field(default=0, alias="sortOrder")
    values: list[ProductSpecValueCreate] = Field(default_factory=list)
    model_config = {"populate_by_name": True}


class InventoryAdjust(BaseModel):
    """后台库存调整请求，正数入库、负数出库。"""

    quantity: Annotated[int, Field(ge=-1_000_000, le=1_000_000)]
    reason: Annotated[str, Field(min_length=1, max_length=200)]

    @field_validator("quantity")
    @classmethod
    def validate_non_zero(cls, value: int) -> int:
        """库存调整不能为零。"""
        if value == 0:
            raise ValueError("调整数量不能为零")
        return value
