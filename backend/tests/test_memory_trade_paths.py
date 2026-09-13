"""开发沙箱交易接口的状态机、金额和归属回归测试。"""

import asyncio
import hashlib
import hmac
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app
from app.services.inventory import InventoryError, InventoryService

client = TestClient(app)


def _order(user_id: str, request_id: str, amount: int = 1299) -> int:
    """创建一笔内存模式订单并返回 ID。"""
    response = client.post(
        "/api/v1/orders",
        headers={
            "Authorization": f"Bearer {create_access_token(user_id)}",
            "X-Request-Id": request_id,
        },
        json={
            "items": [{"skuId": 1, "quantity": 1, "priceCents": amount}],
            "addressSnapshot": {"receiverName": "交易测试"},
            "totalAmount": amount,
        },
    )
    assert response.status_code == 200
    return int(response.json()["data"]["id"])


def test_memory_order_owner_and_transition_errors() -> None:
    """订单详情和状态写操作必须校验归属并拒绝非法流转。"""
    user_id = f"memory-owner-{uuid4().hex}"
    other_user = f"memory-other-{uuid4().hex}"
    order_id = _order(user_id, f"create-{uuid4().hex}")
    owner_token = create_access_token(user_id)
    other_token = create_access_token(other_user)

    assert (
        client.get(f"/api/v1/orders/{order_id}", headers={"Authorization": f"Bearer {other_token}"}).status_code == 404
    )
    assert (
        client.post(
            f"/api/v1/orders/{order_id}/confirm",
            headers={"Authorization": f"Bearer {owner_token}", "X-Request-Id": f"confirm-{uuid4().hex}"},
        ).status_code
        == 409
    )

    cancelled = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {owner_token}", "X-Request-Id": f"cancel-{uuid4().hex}"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "CANCELLED"
    repeated = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={"Authorization": f"Bearer {owner_token}", "X-Request-Id": f"cancel-again-{uuid4().hex}"},
    )
    assert repeated.status_code == 409


def test_memory_payment_amount_signature_and_callback_idempotency() -> None:
    """支付创建校验金额，回调验签并允许同一回调安全重放。"""
    user_id = f"memory-payment-{uuid4().hex}"
    token = create_access_token(user_id)
    order_id = _order(user_id, f"create-{uuid4().hex}", amount=2399)
    payment_headers = {"Authorization": f"Bearer {token}", "X-Request-Id": f"payment-{uuid4().hex}"}
    mismatch = client.post(
        "/api/v1/payments",
        headers=payment_headers,
        json={"orderId": order_id, "provider": "WECHAT", "amountCents": 2400},
    )
    assert mismatch.status_code == 409

    callback_id = f"callback-{uuid4().hex}"
    callback_data = {
        "orderId": order_id,
        "callbackId": callback_id,
        "amountCents": 2399,
        "providerTradeNo": f"trade-{uuid4().hex}",
    }
    payment = client.post(
        "/api/v1/payments",
        headers=payment_headers,
        json={"orderId": order_id, "provider": "WECHAT", "amountCents": 2399},
    )
    assert payment.status_code == 200
    canonical = f"{order_id}:2399:{callback_id}"
    callback_data["signature"] = hmac.new(
        settings.payment_callback_secret.encode(), canonical.encode(), hashlib.sha256
    ).hexdigest()
    callback = client.post("/api/v1/payments/callback", json=callback_data)
    assert callback.status_code == 200
    assert client.post("/api/v1/payments/callback", json=callback_data).status_code == 200

    invalid = {**callback_data, "callbackId": f"invalid-{uuid4().hex}", "signature": "invalid"}
    assert client.post("/api/v1/payments/callback", json=invalid).status_code == 409


def test_inventory_rejects_invalid_quantities_without_mutation() -> None:
    """库存边界失败时不得改变三层库存快照。"""
    service = InventoryService()
    service.seed(7, 3)
    before = service.snapshot(7)
    with pytest.raises(ValueError):
        asyncio.run(service.lock(7, 0))
    with pytest.raises(InventoryError):
        asyncio.run(service.lock(7, 4))
    after = service.snapshot(7)
    assert (after.physical, after.available, after.locked) == (before.physical, before.available, before.locked)
    with pytest.raises(InventoryError):
        asyncio.run(service.release(7, 1))
