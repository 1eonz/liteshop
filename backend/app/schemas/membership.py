"""会员后台写入 DTO。"""

from pydantic import BaseModel, Field


class MemberTagsUpdate(BaseModel):
    """会员标签覆盖请求。"""

    tags: list[str] = Field(default_factory=list, max_length=20)


class MemberLevelUpdate(BaseModel):
    """会员等级更新请求。"""

    member_level: str = Field(alias="memberLevel", pattern="^(NORMAL|MEMBER)$")

    model_config = {"populate_by_name": True}
