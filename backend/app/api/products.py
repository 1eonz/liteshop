"""商品浏览 API。"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..errors.domain import ProductNotFound
from ..services.product_catalog import ProductCatalogService
from .responses import success

router = APIRouter(tags=["products"])
catalog = ProductCatalogService()
_session_dependency = Depends(get_session)

PRODUCTS: list[dict[str, object]] = [
    {
        "id": 1,
        "name": "晨雾保温杯",
        "coverUrl": "",
        "minPrice": 12900,
        "maxPrice": 12900,
        "salesCount": 128,
        "status": "ON_SHELF",
    },
    {
        "id": 2,
        "name": "云朵卫衣",
        "coverUrl": "",
        "minPrice": 26900,
        "maxPrice": 26900,
        "salesCount": 96,
        "status": "ON_SHELF",
    },
    {
        "id": 3,
        "name": "柔光台灯",
        "coverUrl": "",
        "minPrice": 18900,
        "maxPrice": 18900,
        "salesCount": 74,
        "status": "ON_SHELF",
    },
]


def _memory_page(items: list[dict[str, object]], page: int, page_size: int) -> dict[str, object]:
    """为无数据库测试模式构造统一分页响应。"""
    start = (page - 1) * page_size
    sliced = items[start : start + page_size]
    return {
        "items": sliced,
        "meta": {
            "page": page,
            "pageSize": page_size,
            "total": len(items),
            "hasNext": start + page_size < len(items),
        },
    }


@router.get("/products")
async def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """按统一分页格式返回在售商品。"""
    if settings.use_database:
        return success(await catalog.list_products(session, page, page_size))
    return success(_memory_page(PRODUCTS, page, page_size))


@router.get("/products/search")
async def search_products(
    q: str = Query(..., min_length=1, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """按名称关键词搜索在售商品。"""
    if settings.use_database:
        return success(await catalog.list_products(session, page, page_size, keyword=q))
    items = [product for product in PRODUCTS if q in str(product["name"])]
    return success(_memory_page(items, page, page_size))


@router.get("/categories")
async def list_categories(session: AsyncSession = _session_dependency) -> dict[str, object]:
    """返回商品分类列表。"""
    if settings.use_database:
        return success({"items": await catalog.categories(session)})
    return success({"items": []})


@router.get("/products/{product_id}")
async def get_product(product_id: int, session: AsyncSession = _session_dependency) -> dict[str, object]:
    """返回单个商品详情及可售 SKU。"""
    if settings.use_database:
        try:
            return success(await catalog.get(session, product_id))
        except ProductNotFound as exc:
            raise ApiError(
                status_code=404,
                code=40401,
                i18n_key="common.not_found",
                message="商品不存在",
            ) from exc
    product = next((item for item in PRODUCTS if item["id"] == product_id), None)
    if product is None:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="商品不存在",
        )
    return success(
        {
            **product,
            "description": "轻盈材质，适合每日通勤。",
            "detailHtml": "",
            "detailImages": [],
            "skus": [
                {
                    "skuId": 1,
                    "skuCode": "CUP-480",
                    "name": "480ml",
                    "priceCents": product["minPrice"],
                    "quantity": 100,
                    "specs": {"容量": "480ml"},
                }
            ],
        }
    )
