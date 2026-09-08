"""售后 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field

from ..enums.after_sale import AfterSaleType


class AfterSaleCreate(BaseModel):
    """用户创建售后申请。"""

    order_item_id: Annotated[int, Field(alias="orderItemId", gt=0)]
    type: AfterSaleType
    amount_cents: Annotated[int, Field(alias="amountCents", gt=0)]
    reason: str = Field(min_length=1, max_length=500)
    evidence_urls: list[str] = Field(default_factory=list, alias="evidenceUrls", max_length=9)

    model_config = {"populate_by_name": True}


class AfterSaleAudit(BaseModel):
    """后台审核售后申请。"""

    approved: bool
    reason: str = Field(default="", max_length=500)


class AfterSaleReturn(BaseModel):
    """用户提交退货物流。"""

    tracking_no: str = Field(alias="trackingNo", min_length=1, max_length=100)
    model_config = {"populate_by_name": True}
