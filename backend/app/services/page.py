"""低代码页面 Schema 校验和版本迁移。"""

from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.page import PageConversionEvent, PageVariant, StorePage
from ..repositories.page import PageRepository
from ..schemas.page import PageConversionEventInput, PageCreateInput, PageSchemaInput, PageVariantInput


class PageSchemaError(ValueError):
    """页面 Schema 不合法。"""


class PageService:
    """页面 CRUD、危险内容校验与版本迁移。"""

    def __init__(self, repository: PageRepository | None = None) -> None:
        self.repository = repository or PageRepository()

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
        page = await self.repository.get(session, page_id)
        if page is None:
            raise PageSchemaError("页面不存在")
        return self.response(page)

    async def get_by_slug(self, session: AsyncSession, slug: str) -> dict[str, object]:
        """按官网路由读取已发布页面 Schema。"""
        page = await self.repository.get_by_slug(session, slug)
        if page is None:
            raise PageSchemaError("页面不存在")
        return self.response(page)

    async def list_pages(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取页面管理列表。"""
        return [self.list_response(page) for page in await self.repository.list_pages(session)]

    async def create(self, session: AsyncSession, payload: PageCreateInput) -> dict[str, object]:
        """创建页面并校验 slug 唯一性。"""
        if await self.repository.get_by_slug(session, payload.slug) is not None:
            raise PageSchemaError("页面路由已存在")
        self.validate(payload)
        now = datetime.now(UTC)
        page = StorePage(
            slug=payload.slug,
            name=payload.title or payload.slug,
            version=payload.version,
            schema=payload.model_dump(),
            is_home=False,
            created_at=now,
            updated_at=now,
        )
        await self.repository.add(session, page)
        return self.response(page)

    async def save(self, session: AsyncSession, page_id: int, schema: PageSchemaInput) -> dict[str, object]:
        """保存页面并自动更新版本。"""
        self.validate(schema)
        page = await self.repository.get(session, page_id, for_update=True)
        if page is None:
            now = datetime.now(UTC)
            page = StorePage(
                id=page_id,
                slug=schema.slug,
                name=schema.title or schema.slug,
                version=schema.version,
                schema=schema.model_dump(),
                created_at=now,
                updated_at=now,
            )
            await self.repository.add(session, page)
        else:
            page.version = max(page.version + 1, schema.version)
            page.slug = schema.slug
            page.name = schema.title or page.name or schema.slug
            page.schema = schema.model_dump()
            page.updated_at = datetime.now(UTC)
        await self.repository.flush(session)
        return self.response(page)

    async def copy(self, session: AsyncSession, page_id: int, slug: str, name: str | None = None) -> dict[str, object]:
        """复制页面 Schema 到新的 slug。"""
        source = await self.repository.get(session, page_id)
        if source is None:
            raise PageSchemaError("页面不存在")
        if await self.repository.get_by_slug(session, slug) is not None:
            raise PageSchemaError("页面路由已存在")
        now = datetime.now(UTC)
        copied = StorePage(
            slug=slug,
            name=name or f"{source.name or source.slug} 副本",
            version=source.version,
            schema={**source.schema, "slug": slug, "title": name or source.schema.get("title", "")},
            is_home=False,
            created_at=now,
            updated_at=now,
        )
        await self.repository.add(session, copied)
        return self.response(copied)

    async def remove(self, session: AsyncSession, page_id: int) -> dict[str, object]:
        """删除非首页页面。"""
        page = await self.repository.get(session, page_id, for_update=True)
        if page is None:
            raise PageSchemaError("页面不存在")
        if page.is_home:
            raise PageSchemaError("首页不能直接删除，请先设置其他首页")
        await self.repository.delete(session, page_id)
        return {"deleted": True, "id": page_id}

    async def list_variants(self, session: AsyncSession, page_id: int) -> list[dict[str, object]]:
        """读取页面 A/B 变体。"""
        if await self.repository.get(session, page_id) is None:
            raise PageSchemaError("页面不存在")
        return [self.variant_response(item) for item in await self.repository.list_variants(session, page_id)]

    async def save_variant(self, session: AsyncSession, page_id: int, payload: PageVariantInput) -> dict[str, object]:
        """新增或更新页面变体。"""
        if await self.repository.get(session, page_id) is None:
            raise PageSchemaError("页面不存在")
        self.validate(payload.schema_data)
        variant = await self.repository.get_variant(session, page_id, payload.key, for_update=True)
        now = datetime.now(UTC)
        values = {
            "name": payload.name,
            "allocation_percent": payload.allocation_percent,
            "schema": payload.schema_data.model_dump(),
            "enabled": payload.enabled,
        }
        if variant is None:
            variant = PageVariant(page_id=page_id, key=payload.key, created_at=now, updated_at=now, **values)
            await self.repository.add_variant(session, variant)
        else:
            for key, value in values.items():
                setattr(variant, key, value)
            variant.updated_at = now
            await session.flush()
        return self.variant_response(variant)

    async def record_event(
        self, session: AsyncSession, page_id: int, payload: PageConversionEventInput
    ) -> dict[str, object]:
        """记录一次页面转化事件。"""
        if await self.repository.get(session, page_id) is None:
            raise PageSchemaError("页面不存在")
        event = PageConversionEvent(
            page_id=page_id,
            variant_key=payload.variant_key,
            event_name=payload.event_name,
            anonymous_id=payload.anonymous_id,
            event_metadata=payload.metadata,
            created_at=datetime.now(UTC),
        )
        await self.repository.add_conversion_event(session, event)
        return {"id": event.id, "accepted": True}

    async def set_home(self, session: AsyncSession, page_id: int) -> dict[str, object]:
        """原子设置首页。"""
        page = await self.repository.get(session, page_id, for_update=True)
        if page is None:
            raise PageSchemaError("页面不存在")
        await self.repository.clear_home(session)
        page.is_home = True
        await self.repository.flush(session)
        return self.response(page)

    @staticmethod
    def response(page: StorePage) -> dict[str, object]:
        response = dict(page.schema)
        response.update(
            {
                "id": page.id,
                "slug": page.slug,
                "name": page.name,
                "version": page.version,
                "isHome": page.is_home,
            }
        )
        return response

    @staticmethod
    def list_response(page: StorePage) -> dict[str, object]:
        """生成页面列表摘要。"""
        schema = page.schema
        return {
            "id": page.id,
            "slug": page.slug,
            "name": page.name or str(schema.get("title", page.slug)),
            "version": page.version,
            "isHome": page.is_home,
            "updatedAt": page.updated_at.isoformat(),
        }

    @staticmethod
    def variant_response(variant: PageVariant) -> dict[str, object]:
        """生成变体响应。"""
        return {
            "id": variant.id,
            "pageId": variant.page_id,
            "key": variant.key,
            "name": variant.name,
            "allocationPercent": variant.allocation_percent,
            "schema": variant.schema,
            "enabled": variant.enabled,
        }


page_service = PageService()
