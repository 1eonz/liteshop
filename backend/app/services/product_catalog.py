"""商品目录和后台商品维护服务。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.product import Category, ProductSpec, ProductSpecValue, Sku, Spu
from ..repositories.inventory import InventoryRepository
from ..repositories.product import ProductRepository
from ..schemas.products import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate


def _spec_hash(specs: dict[str, str]) -> str:
    """把排序后的规格值编码成稳定哈希，防止同商品重复规格。"""
    canonical = json.dumps(specs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


class ProductCatalogService:
    """在 API 和仓储之间承载商品用例与响应映射。"""

    def __init__(
        self,
        products: ProductRepository | None = None,
        inventory: InventoryRepository | None = None,
    ) -> None:
        self.products = products or ProductRepository()
        self.inventory = inventory or InventoryRepository()

    @staticmethod
    def summary(product: Spu) -> dict[str, object]:
        """生成公开商品摘要。"""
        prices = [sku.price_cents for sku in product.skus if sku.status == "ACTIVE"]
        images = product.main_images
        cover = str(images[0].get("url", "")) if images else ""
        return {
            "id": product.id,
            "name": product.name,
            "coverUrl": cover,
            "minPrice": min(prices, default=0),
            "maxPrice": max(prices, default=0),
            "salesCount": product.sales_count,
            "status": product.status,
        }

    @classmethod
    def detail(cls, product: Spu) -> dict[str, object]:
        """生成商品详情和可选 SKU。"""
        return {
            **cls.summary(product),
            "description": product.description,
            "tags": product.tags,
            "recommendedProductIds": product.recommended_product_ids,
            "subtitle": product.subtitle,
            "brand": product.brand,
            "detailHtml": product.detail_html,
            "detailImages": product.detail_images,
            "seoTitle": product.seo_title,
            "seoDescription": product.seo_description,
            "seoKeywords": product.seo_keywords,
            "specDefinitions": [
                {
                    "id": spec.id,
                    "name": spec.name,
                    "sortOrder": spec.sort_order,
                    "values": [
                        {"id": value.id, "value": value.value, "sortOrder": value.sort_order} for value in spec.values
                    ],
                }
                for spec in product.specs
            ],
            "skus": [
                {
                    "skuId": sku.id,
                    "skuCode": sku.code,
                    "name": sku.name,
                    "priceCents": sku.price_cents,
                    "quantity": sku.available_stock,
                    "specs": sku.spec_values,
                }
                for sku in product.skus
                if sku.status == "ACTIVE"
            ],
        }

    async def list_products(
        self,
        session: AsyncSession,
        page: int,
        page_size: int,
        *,
        keyword: str | None = None,
        include_off_shelf: bool = False,
    ) -> dict[str, object]:
        """分页查询商品并返回统一 meta。"""
        products, total = await self.products.list_spus(
            session,
            (page - 1) * page_size,
            page_size,
            keyword=keyword,
            include_off_shelf=include_off_shelf,
        )
        return {
            "items": [self.summary(product) for product in products],
            "meta": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "hasNext": page * page_size < total,
            },
        }

    async def get(self, session: AsyncSession, product_id: int) -> dict[str, object]:
        """获取商品详情。"""
        return self.detail(await self.products.get_spu(session, product_id))

    async def categories(self, session: AsyncSession) -> list[dict[str, object]]:
        """获取分类列表。"""
        categories = await self.products.list_categories(session)
        return [
            {
                "id": category.id,
                "parentId": category.parent_id,
                "name": category.name,
                "icon": category.icon,
                "sortOrder": category.sort_order,
            }
            for category in categories
        ]

    async def create_category(self, session: AsyncSession, payload: CategoryCreate) -> Category:
        """创建分类。"""
        now = datetime.now(UTC)
        return await self.products.add_category(
            session,
            Category(
                name=payload.name,
                parent_id=payload.parent_id,
                icon=payload.icon,
                sort_order=payload.sort_order,
                is_active=True,
                created_at=now,
                updated_at=now,
            ),
        )

    async def update_category(self, session: AsyncSession, category_id: int, payload: CategoryUpdate) -> Category:
        """更新分类基础信息。"""
        category = await self.products.get_category(session, category_id, for_update=True)
        for field, value in payload.model_dump(exclude_unset=True, by_alias=False).items():
            if value is not None:
                setattr(category, field, value)
        category.updated_at = datetime.now(UTC)
        await self.products.flush(session)
        return category

    async def delete_category(self, session: AsyncSession, category_id: int) -> Category:
        """停用分类，保留历史商品关联。"""
        category = await self.products.get_category(session, category_id, for_update=True)
        category.is_active = False
        category.updated_at = datetime.now(UTC)
        await self.products.flush(session)
        return category

    async def create_product(self, session: AsyncSession, payload: ProductCreate) -> Spu:
        """创建商品及全部 SKU，规格哈希在服务层统一生成。"""
        now = datetime.now(UTC)
        product = Spu(
            category_id=payload.category_id,
            name=payload.name,
            subtitle=payload.subtitle,
            brand=payload.brand,
            main_images=payload.main_images,
            detail_images=payload.detail_images,
            detail_html=payload.detail_html,
            seo_title=payload.seo_title,
            seo_description=payload.seo_description,
            seo_keywords=payload.seo_keywords,
            description=payload.description,
            tags=payload.tags,
            recommended_product_ids=payload.recommended_product_ids,
            status=payload.status,
            created_at=now,
            updated_at=now,
        )
        product.skus = [
            Sku(
                spu=product,
                code=sku.code,
                name=sku.name,
                spec_values=sku.specs,
                spec_hash=_spec_hash(sku.specs),
                price_cents=sku.price_cents,
                cost_cents=sku.cost_cents,
                physical_stock=sku.physical_stock,
                locked_stock=0,
                weight_grams=sku.weight_grams,
                image=sku.image,
                bar_code=sku.bar_code,
                status=sku.status,
                sort_order=sku.sort_order,
                safety_stock=sku.safety_stock,
                created_at=now,
                updated_at=now,
            )
            for sku in payload.skus
        ]
        product.specs = [
            ProductSpec(
                name=spec.name,
                sort_order=spec.sort_order,
                values=[ProductSpecValue(value=value.value, sort_order=value.sort_order) for value in spec.values],
            )
            for spec in payload.specs
        ]
        return await self.products.add_product(session, product)

    async def update_product(self, session: AsyncSession, product_id: int, payload: ProductUpdate) -> Spu:
        """更新 SPU 基础字段；SKU 独立库存不能通过此接口覆盖。"""
        product = await self.products.get_spu(session, product_id, for_update=True)
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        for field, value in changes.items():
            setattr(product, field, value)
        product.updated_at = datetime.now(UTC)
        await self.products.flush(session)
        return product

    async def soft_delete_product(self, session: AsyncSession, product_id: int) -> Spu:
        """软删除商品，保留订单快照关联。"""
        product = await self.products.get_spu(session, product_id, for_update=True)
        product.status = "OFF_SHELF"
        product.deleted_at = datetime.now(UTC)
        product.updated_at = product.deleted_at
        await self.products.flush(session)
        return product
