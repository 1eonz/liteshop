"""商品发布状态枚举。"""

from enum import StrEnum


class ProductStatus(StrEnum):
    """商品 SPU 发布状态。"""

    DRAFT = "DRAFT"
    ON_SHELF = "ON_SHELF"
    OFF_SHELF = "OFF_SHELF"
