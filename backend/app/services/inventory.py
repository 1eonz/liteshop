"""三层库存模型与并发安全操作。"""

import asyncio
from dataclasses import dataclass


class InventoryError(RuntimeError):
    """库存不足或状态不满足操作条件。"""


@dataclass
class Inventory:
    """单个 SKU 的实物、可售和锁定库存。"""

    physical: int
    available: int
    locked: int = 0


class InventoryService:
    """使用 SKU 级锁保证库存扣减的原子性。"""

    def __init__(self) -> None:
        self._items: dict[int, Inventory] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def seed(self, sku_id: int, quantity: int) -> None:
        """初始化库存，三层库存保持一致。"""
        if quantity < 0:
            raise ValueError("库存不能为负数")
        self._items[sku_id] = Inventory(physical=quantity, available=quantity)
        self._locks.setdefault(sku_id, asyncio.Lock())

    async def lock(self, sku_id: int, quantity: int) -> None:
        """锁定可售库存，数量不足时不改变任何值。"""
        if quantity <= 0:
            raise ValueError("锁定数量必须大于零")
        async with self._locks.setdefault(sku_id, asyncio.Lock()):
            item = self._items[sku_id]
            if item.available < quantity:
                raise InventoryError("库存不足")
            item.available -= quantity
            item.locked += quantity

    async def release(self, sku_id: int, quantity: int) -> None:
        """释放锁定库存回到可售库存。"""
        async with self._locks.setdefault(sku_id, asyncio.Lock()):
            item = self._items[sku_id]
            if item.locked < quantity:
                raise InventoryError("锁定库存不足")
            item.locked -= quantity
            item.available += quantity

    async def deduct(self, sku_id: int, quantity: int) -> None:
        """将锁定库存扣减为实物库存。"""
        async with self._locks.setdefault(sku_id, asyncio.Lock()):
            item = self._items[sku_id]
            if item.locked < quantity:
                raise InventoryError("锁定库存不足")
            item.locked -= quantity
            item.physical -= quantity

    def snapshot(self, sku_id: int) -> Inventory:
        """读取库存快照。"""
        item = self._items[sku_id]
        return Inventory(item.physical, item.available, item.locked)
