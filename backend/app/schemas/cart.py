"""购物车 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field


class CartItemInput(BaseModel):
    """添加或更新购物车项。"""

    sku_id: Annotated[int, Field(alias="skuId", gt=0)]
    quantity: Annotated[int, Field(gt=0, le=999)]
    price_cents: Annotated[int, Field(alias="priceCents", ge=0)]
    model_config = {"populate_by_name": True}


class CartItemResponse(BaseModel):
    """购物车展示项，金额仍为整数分。"""

    id: int
    sku_id: int = Field(alias="skuId")
    quantity: int
    price_cents: int = Field(alias="priceCents")
    stale: bool = False
    model_config = {"populate_by_name": True}
