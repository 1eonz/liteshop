"""低代码页面 Schema 校验和版本迁移。"""

from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.page import StorePage
from ..schemas.page import PageSchemaInput


class PageSchemaError(ValueError):
    """页面 Schema 不合法。"""


class PageService:
    """页面 CRUD、危险内容校验与版本迁移。"""

    @staticmethod
    def validate(schema: PageSchemaInput) -> None:
        """拒绝危险 URL、脚本和非 token 样式。"""
        for component in schema.components:
            serialized = str(component.props).lower()
            if "javascript:" in serialized or "<script" in serialized:
                raise PageSchemaError("页面内容包含危险脚本")
            for key, value in component.style.items():
                if key not in {"color", "backgroundColor", "fontSize", "padding", "margin", "borderRadius"}:
                    raise PageSchemaError("页面样式属性不受支持")
                if value.startswith("#") or value.endswith("px"):
                    raise PageSchemaError("页面样式必须使用 Design Token")
            for prop_value in component.props.values():
                if isinstance(prop_value, str) and prop_value.startswith(("http://", "https://")):
                    parsed = urlparse(prop_value)
                    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                        raise PageSchemaError("页面 URL 不合法")

    async def get(self, session: AsyncSession, page_id: int) -> dict[str, object]:
        """读取页面 Schema。"""
        page = await session.get(StorePage, page_id)
        if page is None:
            raise PageSchemaError("页面不存在")
        return self.response(page)

    async def save(self, session: AsyncSession, page_id: int, schema: PageSchemaInput) -> dict[str, object]:
        """保存页面并自动更新版本。"""
        self.validate(schema)
        page = await session.get(StorePage, page_id, with_for_update=True)
        if page is None:
            now = datetime.now(UTC)
            page = StorePage(
                id=page_id,
                slug=schema.slug,
                version=schema.version,
                schema=schema.model_dump(),
                created_at=now,
                updated_at=now,
            )
            session.add(page)
        else:
            page.version = max(page.version + 1, schema.version)
            page.slug = schema.slug
            page.schema = schema.model_dump()
            page.updated_at = datetime.now(UTC)
        await session.flush()
        return self.response(page)

    async def set_home(self, session: AsyncSession, page_id: int) -> dict[str, object]:
        """原子设置首页。"""
        page = await session.get(StorePage, page_id, with_for_update=True)
        if page is None:
            raise PageSchemaError("页面不存在")
        await session.execute(update(StorePage).values(is_home=False))
        page.is_home = True
        await session.flush()
        return self.response(page)

    @staticmethod
    def response(page: StorePage) -> dict[str, object]:
        return {"id": page.id, "slug": page.slug, "version": page.version, "isHome": page.is_home, **page.schema}


page_service = PageService()
