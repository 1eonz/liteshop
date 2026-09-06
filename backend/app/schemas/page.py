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
    version: int = Field(ge=1)
    components: list[PageComponent] = Field(max_length=50)
