"""支付 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field

from ..enums.payment import PaymentProvider


class PaymentCreate(BaseModel):
    """创建支付单请求。"""

    order_id: Annotated[int, Field(alias="orderId", gt=0)]
    provider: PaymentProvider
    amount_cents: Annotated[int, Field(alias="amountCents", ge=0)]
    model_config = {"populate_by_name": True}


class PaymentCallback(BaseModel):
    """支付回调统一输入，provider 适配器可在入口前转换。"""

    order_id: Annotated[int, Field(alias="orderId", gt=0)]
    callback_id: Annotated[str, Field(alias="callbackId", min_length=1, max_length=128)]
    amount_cents: Annotated[int, Field(alias="amountCents", ge=0)]
    signature: str = Field(min_length=1)
    provider_trade_no: str = Field(alias="providerTradeNo", min_length=1, max_length=128)
    model_config = {"populate_by_name": True}


class RefundCreate(BaseModel):
    """创建退款申请，金额为整数分。"""

    amount_cents: Annotated[int, Field(alias="amountCents", gt=0)]
    reason: str = Field(default="用户申请退款", max_length=500)
    model_config = {"populate_by_name": True}


class RefundResponse(BaseModel):
    """退款申请响应。"""

    id: int
    refund_no: str = Field(alias="refundNo")
    payment_id: int = Field(alias="paymentId")
    amount_cents: int = Field(alias="amountCents")
    status: str
    model_config = {"populate_by_name": True}
