"""订单 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field, model_validator


class OrderItemCreate(BaseModel):
    """下单商品输入，价格为客户端确认的整数分。"""

    sku_id: Annotated[int, Field(alias="skuId", gt=0)]
    quantity: Annotated[int, Field(gt=0, le=999)]
    price_cents: Annotated[int, Field(alias="priceCents", ge=0)]
    model_config = {"populate_by_name": True}


class OrderCreate(BaseModel):
    """订单创建请求。"""

    items: Annotated[list[OrderItemCreate], Field(min_length=1)]
    address_snapshot: dict[str, str] = Field(alias="addressSnapshot")
    total_amount: Annotated[int, Field(alias="totalAmount", ge=0)]
    product_amount: Annotated[int | None, Field(alias="productAmount", ge=0)] = None
    freight_amount: Annotated[int, Field(alias="freightAmount", ge=0)] = 0
    remark: str | None = Field(default=None, max_length=500)
    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def validate_unique_skus(self) -> "OrderCreate":
        """同一订单不允许重复 SKU，避免库存和快照出现歧义。"""
        sku_ids = [item.sku_id for item in self.items]
        if len(sku_ids) != len(set(sku_ids)):
            raise ValueError("订单商品包含重复 SKU")
        return self


class OrderResponse(BaseModel):
    """订单最小响应 DTO。"""

    id: int
    order_no: str = Field(alias="orderNo")
    status: str
    total_amount: int = Field(alias="totalAmount")
    refund_status: str = Field(alias="refundStatus")
    product_amount: int = Field(alias="productAmount")
    freight_amount: int = Field(alias="freightAmount")
    discount_amount: int = Field(alias="discountAmount")
    paid_amount: int | None = Field(default=None, alias="paidAmount")
    paid_at: str | None = Field(default=None, alias="paidAt")
    shipped_at: str | None = Field(default=None, alias="shippedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    cancelled_at: str | None = Field(default=None, alias="cancelledAt")
    cancel_reason: str | None = Field(default=None, alias="cancelReason")
    address_snapshot: dict[str, str] = Field(alias="addressSnapshot")
    remark: str | None = None
    model_config = {"populate_by_name": True}
