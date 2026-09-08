"""商品评价商家回复的状态约束测试。"""

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.review import ReviewRepository
from app.services.review import ReviewError, ReviewService


def _review(status: str) -> SimpleNamespace:
    """构造商家回复所需的最小评价对象。"""
    return SimpleNamespace(
        id=7,
        status=status,
        merchant_reply=None,
        merchant_replied_at=None,
        updated_at=datetime.now(UTC),
    )


def test_reply_requires_approved_review() -> None:
    """未审核通过的评价不能展示商家回复。"""
    review = _review("PENDING")
    repository = SimpleNamespace(get_for_update=AsyncMock(return_value=review), flush=AsyncMock())
    service = ReviewService(repository=cast(ReviewRepository, repository))
    with pytest.raises(ReviewError, match="只有已通过评价可以回复"):
        asyncio.run(service.reply(cast(AsyncSession, AsyncMock()), 7, "感谢支持"))


def test_reply_updates_content_and_timestamp() -> None:
    """已通过评价保存回复后返回统一响应字段。"""
    review = _review("APPROVED")
    repository = SimpleNamespace(get_for_update=AsyncMock(return_value=review), flush=AsyncMock())
    service = ReviewService(repository=cast(ReviewRepository, repository))
    response = asyncio.run(service.reply(cast(AsyncSession, AsyncMock()), 7, "  感谢支持  "))
    assert response["id"] == 7
    assert response["merchantReply"] == "感谢支持"
    assert review.merchant_reply == "感谢支持"
    assert review.merchant_replied_at is not None
