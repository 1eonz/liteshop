"""AI 商品文案建议 API。"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..services.ai_copy import product_copy_provider
from .responses import success

router = APIRouter(prefix="/ai/product-copy", tags=["ai"])


class ProductCopyRequest(BaseModel):
    """商品文案生成请求。"""

    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="", max_length=100)


@router.post("")
async def generate_product_copy(payload: ProductCopyRequest) -> dict[str, object]:
    """生成可人工审核的商品文案草稿。"""
    suggestion = await product_copy_provider.generate(name=payload.name, category=payload.category)
    return success(
        {
            "title": suggestion.title,
            "subtitle": suggestion.subtitle,
            "description": suggestion.description,
            "provider": suggestion.provider,
            "requiresReview": True,
        }
    )
