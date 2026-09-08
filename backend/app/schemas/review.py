"""商品评价 DTO。"""

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """用户评价订单项请求。"""

    order_item_id: int = Field(alias="orderItemId", gt=0)
    rating: int = Field(ge=1, le=5)
    content: str = Field(default="", max_length=2000)
    images: list[str] = Field(default_factory=list, max_length=9)

    model_config = {"populate_by_name": True}


class ReviewAudit(BaseModel):
    """后台评价审核请求。"""

    status: str = Field(pattern="^(APPROVED|REJECTED)$")
    reason: str = Field(default="", max_length=500)


class ReviewReply(BaseModel):
    """商家回复已通过评价。"""

    reply: str = Field(min_length=1, max_length=2000)
