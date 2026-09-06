"""Pydantic request and response schemas."""

from .admin import FeatureFlagUpdate, OrderPriceUpdate, ShipOrderRequest
from .auth import LoginRequest, SmsCodeRequest
from .cart import CartItemInput, CartItemResponse
from .orders import OrderCreate, OrderItemCreate, OrderResponse
from .payments import PaymentCallback, PaymentCreate, RefundCreate, RefundResponse
from .products import (
    CategoryCreate,
    InventoryAdjust,
    ProductCreate,
    ProductSpecCreate,
    ProductSpecValueCreate,
    ProductUpdate,
    SkuCreate,
)
from .uploads import UploadSignRequest
from .users import AddressCreate, AddressUpdate

__all__ = [
    "LoginRequest",
    "FeatureFlagUpdate",
    "OrderPriceUpdate",
    "ShipOrderRequest",
    "CartItemInput",
    "CartItemResponse",
    "OrderCreate",
    "OrderItemCreate",
    "OrderResponse",
    "PaymentCallback",
    "PaymentCreate",
    "RefundCreate",
    "RefundResponse",
    "CategoryCreate",
    "AddressCreate",
    "AddressUpdate",
    "InventoryAdjust",
    "ProductCreate",
    "ProductUpdate",
    "ProductSpecCreate",
    "ProductSpecValueCreate",
    "SkuCreate",
    "SmsCodeRequest",
    "UploadSignRequest",
]
