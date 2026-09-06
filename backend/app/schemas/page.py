"""低代码页面 Schema DTO。"""

from pydantic import BaseModel, Field, field_validator

ALLOWED_COMPONENTS = {
    "SearchBar",
    "Carousel",
    "CategoryGrid",
    "ProductGrid",
    "ActivityBanner",
    "Tabbar",
    "RichText",
    "ImageBanner",
    "Spacer",
    "ProductList",
    "ProductCarousel",
    "CouponBlock",
    "AnnouncementBar",
}


class PageComponent(BaseModel):
    """单个低代码组件。"""

    id: str = Field(min_length=1, max_length=64)
    type: str = Field(min_length=1, max_length=40)
    props: dict[str, object] = Field(default_factory=dict)
    style: dict[str, str] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if value not in ALLOWED_COMPONENTS:
            raise ValueError("不支持的页面组件")
        return value


class PageSchemaInput(BaseModel):
    """页面 Schema 保存请求。"""

    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    title: str = Field(default="", max_length=120)
    seo: dict[str, object] = Field(default_factory=dict)
    version: int = Field(ge=1)
    components: list[PageComponent] = Field(max_length=50)


class PageCreateInput(PageSchemaInput):
    """创建商城页面请求。"""


class PageCopyInput(BaseModel):
    """复制页面请求。"""

    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    name: str = Field(default="", max_length=120)


class PageVariantInput(BaseModel):
    """保存页面变体请求。"""

    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    allocation_percent: int = Field(default=0, ge=0, le=100, alias="allocationPercent")
    schema_data: PageSchemaInput = Field(alias="schema")
    enabled: bool = True
    model_config = {"populate_by_name": True}


class PageConversionEventInput(BaseModel):
    """页面转化事件上报请求。"""

    variant_key: str = Field(default="control", max_length=40, alias="variantKey")
    event_name: str = Field(min_length=1, max_length=80, alias="eventName")
    anonymous_id: str = Field(default="", max_length=100, alias="anonymousId")
    metadata: dict[str, object] = Field(default_factory=dict)
    model_config = {"populate_by_name": True}
