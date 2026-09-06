"""库存流水事件枚举。"""

from enum import StrEnum


class InventoryEventType(StrEnum):
    """三层库存变化的原因。"""

    LOCK = "LOCK"
    DEDUCT = "DEDUCT"
    RELEASE = "RELEASE"
    PURCHASE_IN = "PURCHASE_IN"
    MANUAL_ADJUST = "MANUAL_ADJUST"
