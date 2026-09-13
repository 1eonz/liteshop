"""管理后台商品与分类路由。"""

from fastapi import APIRouter, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.products import CategoryCreate, CategoryUpdate, ProductCreate, ProductUpdate
from ..dependencies import CurrentSubject
from ..responses import success
from .common import admin_service, authorize_read, execute_write, require_database, session_dependency

router = APIRouter()


@router.get("/products")
async def list_products(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    q: str | None = Query(None, min_length=1, max_length=100),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """后台商品列表。"""
    require_database()
    await authorize_read(session, subject, "product.read")
    return success(
        await admin_service.catalog.list_products(session, page, page_size, keyword=q, include_off_shelf=True)
    )


@router.post("/categories")
async def create_category(
    payload: CategoryCreate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """创建商品分类。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_category_create",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.create_category(
            session, payload, user_id, request_id
        ),
    )


@router.get("/categories")
async def list_categories(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """后台分类管理列表。"""
    require_database()
    await authorize_read(session, subject, "product.read")
    return success({"items": await admin_service.list_categories(session)})


@router.put("/categories/{category_id}")
async def update_category(
    category_id: int, payload: CategoryUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """更新后台商品分类。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_category_update:{category_id}",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.update_category(
            session, category_id, payload, user_id, request_id
        ),
    )


@router.delete("/categories/{category_id}")
async def delete_category(
    category_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """停用后台商品分类。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_category_delete:{category_id}",
        permission="product.write",
        resource_type="category",
        operation=lambda session, user_id, request_id: admin_service.delete_category(
            session, category_id, user_id, request_id
        ),
    )


@router.post("/products")
async def create_product(
    payload: ProductCreate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """创建商品及 SKU。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_product_create",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.create_product(
            session, payload, user_id, request_id
        ),
    )


@router.put("/products/{product_id}")
async def update_product(
    product_id: int, payload: ProductUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """更新商品基础字段。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_product_update:{product_id}",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.update_product(
            session, product_id, payload, user_id, request_id
        ),
    )


@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """软删除商品。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_product_delete:{product_id}",
        permission="product.write",
        resource_type="product",
        operation=lambda session, user_id, request_id: admin_service.delete_product(
            session, product_id, user_id, request_id
        ),
    )
