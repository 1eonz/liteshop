"""物流轨迹请求 DTO。"""

from datetime import datetime

from pydantic import BaseModel, Field


class TrackingEventCreate(BaseModel):
    """写入物流节点。"""

    status: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=500)
    location: str = Field(default="", max_length=120)
    occurred_at: datetime = Field(alias="occurredAt")
    model_config = {"populate_by_name": True}
