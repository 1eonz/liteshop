"""真实数据库模式下的 HTTP API 边界验收。

运行前启动 PostgreSQL/Redis，并设置 LITESHOP_RUN_INTEGRATION=1、
LITESHOP_USE_DATABASE=true。测试只读取公共接口，避免污染开发数据。
"""

import os
from collections.abc import AsyncIterator

import httpx
import pytest

from app.main import app
from app.core.database import engine

pytestmark = pytest.mark.skipif(
    os.getenv("LITESHOP_RUN_INTEGRATION") != "1"
    or os.getenv("LITESHOP_USE_DATABASE", "false").lower() != "true",
    reason="设置 LITESHOP_RUN_INTEGRATION=1 且启用真实数据库后运行",
)


@pytest.fixture
def anyio_backend() -> str:
    """真实数据库集成测试固定使用 asyncio，避免跨事件循环复用连接。"""
    return "asyncio"


@pytest.fixture(autouse=True)
async def reset_database_engine() -> AsyncIterator[None]:
    """每个测试前后清理应用连接池，避免 Windows 事件循环复用连接。"""
    await engine.dispose()
    yield
    await engine.dispose()


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    """通过 ASGI transport 发起真实 HTTP 路由调用。"""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.anyio
async def test_products_pagination_and_empty_search(api_client: httpx.AsyncClient) -> None:
    """验证数据库商品分页和无结果搜索的统一响应结构。"""
    response = await api_client.get("/api/v1/products", params={"page": 1, "pageSize": 1})
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["meta"]["page"] == 1
    assert body["data"]["meta"]["pageSize"] == 1
    assert len(body["data"]["items"]) <= 1

    empty = await api_client.get("/api/v1/products/search", params={"q": "__不存在的唯一关键词__"})
    assert empty.status_code == 200
    assert empty.json()["code"] == 0
    assert empty.json()["data"]["items"] == []


@pytest.mark.anyio
async def test_products_query_boundaries_and_not_found(api_client: httpx.AsyncClient) -> None:
    """验证分页上下界、非法参数和商品不存在错误码。"""
    for params in ({"page": 0}, {"pageSize": 0}, {"pageSize": 101}):
        response = await api_client.get("/api/v1/products", params=params)
        assert response.status_code == 422

    missing = await api_client.get("/api/v1/products/2147483647")
    assert missing.status_code == 404
    payload = missing.json()
    assert payload["code"] == 40401
    assert "data" not in payload
    assert payload["requestId"]


@pytest.mark.anyio
async def test_categories_and_protected_order_boundary(api_client: httpx.AsyncClient) -> None:
    """验证分类接口可返回空数组，以及订单接口拒绝匿名访问。"""
    categories = await api_client.get("/api/v1/categories")
    assert categories.status_code == 200
    assert isinstance(categories.json()["data"]["items"], list)

    orders = await api_client.get("/api/v1/orders", params={"page": 1, "pageSize": 1})
    assert orders.status_code == 401
    assert orders.json()["code"] in {40101, 40102}
