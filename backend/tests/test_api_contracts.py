"""商品、订单和支付 API 契约测试。"""

import hashlib
import hmac

from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_product_list_and_search() -> None:
    """商品列表和搜索返回统一分页字段。"""
    response = client.get("/api/v1/products?page=1&pageSize=2")
    assert response.status_code == 200
    assert set(response.json()) == {"code", "message", "data", "requestId"}
    assert response.json()["data"]["meta"]["pageSize"] == 2
    assert client.get("/api/v1/products/search?q=保温").json()["data"]["meta"]["total"] == 1


def test_order_idempotency_and_payment_callback() -> None:
    """相同请求 ID 返回相同订单，支付回调验签并幂等。"""
    token = create_access_token("user-1")
    headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "request-1"}
    order_payload = {
        "items": [{"skuId": 1, "quantity": 1, "priceCents": 12900}],
        "addressSnapshot": {"receiverName": "测试用户"},
        "totalAmount": 12900,
    }
    first = client.post("/api/v1/orders", headers=headers, json=order_payload)
    second = client.post("/api/v1/orders", headers=headers, json=order_payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["id"] == second.json()["data"]["id"]
    order_id = first.json()["data"]["id"]
    payment = client.post(
        "/api/v1/payments",
        headers={"Authorization": f"Bearer {token}", "X-Request-Id": "payment-request-1"},
        json={"orderId": order_id, "provider": "WECHAT", "amountCents": 12900},
    )
    assert payment.status_code == 200
    callback_id = "callback-1"
    payload = f"{order_id}:12900:{callback_id}"
    signature = hmac.new(settings.payment_callback_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    callback = client.post(
        "/api/v1/payments/callback",
        json={
            "orderId": order_id,
            "callbackId": callback_id,
            "amountCents": 12900,
            "signature": signature,
            "providerTradeNo": "trade-1",
        },
    )
    assert callback.status_code == 200
    assert (
        client.post(
            "/api/v1/payments/callback",
            json={
                "orderId": order_id,
                "callbackId": callback_id,
                "amountCents": 12900,
                "signature": signature,
                "providerTradeNo": "trade-1",
            },
        ).status_code
        == 200
    )
    rejected = client.post(
        "/api/v1/payments/callback",
        json={
            "orderId": order_id,
            "callbackId": callback_id,
            "amountCents": 12900,
            "signature": "invalid-signature",
            "providerTradeNo": "trade-1",
        },
    )
    assert rejected.status_code == 409


def test_cart_write_is_idempotent() -> None:
    """重复加购请求返回相同快照且不重复累加。"""
    token = create_access_token("cart-user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "cart-request-1"}
    payload = {"skuId": 1, "quantity": 2, "priceCents": 12900}
    first = client.post("/api/v1/cart/items", headers=headers, json=payload)
    second = client.post("/api/v1/cart/items", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    cart = client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert cart.json()["data"]["items"][0]["quantity"] == 2


def test_upload_signature_validates_and_is_idempotent() -> None:
    """上传签名校验白名单，相同请求 ID 返回相同对象地址。"""
    token = create_access_token("upload-user")
    headers = {"Authorization": f"Bearer {token}", "X-Request-Id": "upload-request-1"}
    payload = {"fileName": "product.webp", "fileSize": 1024, "contentType": "image/webp"}
    first = client.post("/api/v1/upload/sign", headers=headers, json=payload)
    second = client.post("/api/v1/upload/sign", headers=headers, json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["data"]["fileUrl"] == second.json()["data"]["fileUrl"]
    rejected = client.post(
        "/api/v1/upload/sign",
        headers={"Authorization": f"Bearer {token}", "X-Request-Id": "upload-request-2"},
        json={"fileName": "payload.exe", "fileSize": 1024, "contentType": "application/octet-stream"},
    )
    assert rejected.status_code == 400
