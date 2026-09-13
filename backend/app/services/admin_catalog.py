"""管理后台商品与分类领域服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.products import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate
from .admin_core import AdminServiceCore


class AdminCatalogService(AdminServiceCore):
    """编排商品与分类写操作及审计记录。"""

    async def list_products(self, session: AsyncSession, page: int, page_size: int) -> dict[str, object]:
        """后台读取全部未删除商品。"""
        return await self.catalog.list_products(session, page, page_size, include_off_shelf=True)

    async def create_category(
        self, session: AsyncSession, payload: CategoryCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建分类并记录审计日志。"""
        category = await self.catalog.create_category(session, payload)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data={"id": category.id, "name": category.name},
        )
        return {"id": category.id, "name": category.name}

    async def list_categories(self, session: AsyncSession) -> list[dict[str, object]]:
        """读取后台分类管理列表。"""
        return await self.catalog.categories(session)

    async def update_category(
        self, session: AsyncSession, category_id: int, payload: CategoryUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新分类并记录审计日志。"""
        category = await self.catalog.update_category(session, category_id, payload)
        response: dict[str, object] = {
            "id": category.id,
            "parentId": category.parent_id,
            "name": category.name,
            "icon": category.icon,
            "sortOrder": category.sort_order,
            "isActive": category.is_active,
        }
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category_id,
            action="UPDATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def delete_category(
        self, session: AsyncSession, category_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """停用分类并记录审计日志。"""
        category = await self.catalog.delete_category(session, category_id)
        response: dict[str, object] = {"deleted": True, "categoryId": category.id}
        await self.audit(
            session,
            user_id=user_id,
            resource_type="CATEGORY",
            resource_id=category_id,
            action="DELETE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def create_product(
        self, session: AsyncSession, payload: ProductCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建商品和 SKU 并记录审计日志。"""
        product = await self.catalog.create_product(session, payload)
        response = self.catalog.detail(product)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_product(
        self, session: AsyncSession, product_id: int, payload: ProductUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新商品基础信息并记录审计日志。"""
        current = await self.catalog.products.get_spu(session, product_id, for_update=True)
        before_data = self.catalog.detail(current)
        product = await self.catalog.update_product(session, product_id, payload)
        after_data = self.catalog.detail(product)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product_id,
            action="UPDATE",
            request_id=request_id,
            before_data=before_data,
            after_data=after_data,
        )
        return after_data

    async def delete_product(
        self, session: AsyncSession, product_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """软删除商品并记录审计日志。"""
        current = await self.catalog.products.get_spu(session, product_id, for_update=True)
        before_data = self.catalog.detail(current)
        product = await self.catalog.soft_delete_product(session, product_id)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="PRODUCT",
            resource_id=product_id,
            action="DELETE",
            request_id=request_id,
            before_data=before_data,
            after_data=self.catalog.detail(product),
        )
        return {"deleted": True, "productId": product_id}
