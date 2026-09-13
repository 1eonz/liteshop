"""订单聚合路由的契约兼容回归测试。"""

from app.main import app

EXPECTED_ORDER_OPERATIONS = [
    ("POST", "/api/v1/orders", "create_order_api_v1_orders_post"),
    ("GET", "/api/v1/orders", "list_orders_api_v1_orders_get"),
    ("POST", "/api/v1/orders/freight-calc", "calculate_freight_api_v1_orders_freight_calc_post"),
    ("GET", "/api/v1/orders/{order_id}", "get_order_api_v1_orders__order_id__get"),
    ("POST", "/api/v1/orders/{order_id}/cancel", "cancel_order_api_v1_orders__order_id__cancel_post"),
    ("POST", "/api/v1/orders/{order_id}/confirm", "confirm_order_api_v1_orders__order_id__confirm_post"),
    ("POST", "/api/v1/payments", "create_payment_api_v1_payments_post"),
    ("POST", "/api/v1/payments/{payment_id}/refund", "create_refund_api_v1_payments__payment_id__refund_post"),
    ("POST", "/api/v1/payments/callback", "payment_callback_api_v1_payments_callback_post"),
    ("POST", "/api/v1/payments/wechat/callback", "wechat_callback_api_v1_payments_wechat_callback_post"),
    ("POST", "/api/v1/payments/alipay/callback", "alipay_callback_api_v1_payments_alipay_callback_post"),
]


def test_order_router_keeps_paths_methods_order_and_tags() -> None:
    """拆分领域模块后仍保持原路由注册顺序和外部契约。"""
    actual: list[tuple[str, str, str]] = []
    for path, path_item in app.openapi()["paths"].items():
        for method, operation in path_item.items():
            if operation.get("tags") == ["orders"]:
                actual.append((method.upper(), path, operation["operationId"]))

    assert actual == EXPECTED_ORDER_OPERATIONS
