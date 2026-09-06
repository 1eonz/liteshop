"""库存仓储：使用行锁和条件校验保证三层库存一致。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Executable, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..enums.inventory import InventoryEventType
from ..models.inventory import InventoryLedger
from ..models.product import Sku


class InventoryRepositoryError(RuntimeError):
    """库存仓储基础异常。"""


class InventoryNotFound(InventoryRepositoryError):
    """SKU 不存在。"""


class InsufficientStock(InventoryRepositoryError):
    """可售或锁定库存不足。"""


class InventoryRepository:
    """在调用方事务中执行库存原子变更。"""

    async def _raise_stock_error(self, session: AsyncSession, sku_id: int) -> None:
        """区分 SKU 不存在与条件库存不足。"""
        exists = await session.scalar(select(Sku.id).where(Sku.id == sku_id))
        if exists is None:
            raise InventoryNotFound(f"SKU {sku_id} 不存在")
        raise InsufficientStock(f"SKU {sku_id} 库存不足")

    async def _ledger(
        self,
        session: AsyncSession,
        sku: Sku,
        event_type: InventoryEventType,
        quantity: int,
        reference_no: str,
        request_id: str,
        *,
        physical_before: int,
        locked_before: int,
        reason: str | None = None,
        operator_id: int | None = None,
    ) -> InventoryLedger:
        """同时写入旧兼容列和 E3.1.3 规范列。"""
        source_type = {
            InventoryEventType.LOCK: "ORDER_LOCK",
            InventoryEventType.DEDUCT: "ORDER_SHIP",
            InventoryEventType.RELEASE: "ORDER_CANCEL",
            InventoryEventType.PURCHASE_IN: "PURCHASE",
            InventoryEventType.MANUAL_ADJUST: "MANUAL",
        }[event_type]
        change_type = {
            InventoryEventType.LOCK: "LOCK",
            InventoryEventType.DEDUCT: "SHIP",
            InventoryEventType.RELEASE: "UNLOCK",
            InventoryEventType.PURCHASE_IN: "INBOUND",
            InventoryEventType.MANUAL_ADJUST: "ADJUST",
        }[event_type]
        source_id = int(reference_no) if reference_no.isdecimal() else None
        entry = InventoryLedger(
            sku_id=sku.id,
            event_type=event_type.value,
            quantity=quantity,
            physical_before=physical_before,
            physical_after=sku.physical_stock,
            locked_before=locked_before,
            locked_after=sku.locked_stock,
            reference_no=reference_no,
            request_id=request_id,
            source_type=source_type,
            source_id=source_id,
            change_type=change_type,
            change_qty=quantity,
            operator_id=operator_id,
            reason=reason,
            created_at=datetime.now(UTC),
        )
        session.add(entry)
        await session.flush()
        return entry

    async def _updated_sku(self, session: AsyncSession, statement: Executable, sku_id: int) -> Sku | None:
        """执行带条件的原子更新，并读取本事务内的新快照。"""
        result = await session.execute(statement)
        if result.first() is None:
            return None
        return cast(
            Sku | None,
            await session.scalar(select(Sku).where(Sku.id == sku_id).execution_options(populate_existing=True)),
        )

    async def lock(self, session: AsyncSession, sku_id: int, quantity: int, reference_no: str, request_id: str) -> Sku:
        """锁定可售库存；不足时事务内不修改任何库存字段。"""
        if quantity <= 0:
            raise ValueError("库存数量必须大于零")
        sku = await self._updated_sku(
            session,
            update(Sku)
            .where(Sku.id == sku_id, Sku.physical_stock - Sku.locked_stock >= quantity)
            .values(locked_stock=Sku.locked_stock + quantity)
            .returning(Sku.id),
            sku_id,
        )
        if sku is None:
            await self._raise_stock_error(session, sku_id)
            raise AssertionError("库存错误分支应已抛出异常")
        await self._ledger(
            session,
            sku,
            InventoryEventType.LOCK,
            quantity,
            reference_no,
            request_id,
            physical_before=sku.physical_stock,
            locked_before=sku.locked_stock - quantity,
        )
        return sku

    async def release(
        self, session: AsyncSession, sku_id: int, quantity: int, reference_no: str, request_id: str
    ) -> Sku:
        """释放锁定库存回到可售库存。"""
        if quantity <= 0:
            raise ValueError("库存数量必须大于零")
        sku = await self._updated_sku(
            session,
            update(Sku)
            .where(Sku.id == sku_id, Sku.locked_stock >= quantity)
            .values(locked_stock=Sku.locked_stock - quantity)
            .returning(Sku.id),
            sku_id,
        )
        if sku is None:
            await self._raise_stock_error(session, sku_id)
            raise AssertionError("库存错误分支应已抛出异常")
        await self._ledger(
            session,
            sku,
            InventoryEventType.RELEASE,
            quantity,
            reference_no,
            request_id,
            physical_before=sku.physical_stock,
            locked_before=sku.locked_stock + quantity,
        )
        return sku

    async def deduct(
        self, session: AsyncSession, sku_id: int, quantity: int, reference_no: str, request_id: str
    ) -> Sku:
        """将锁定库存转为已扣减实物库存。"""
        if quantity <= 0:
            raise ValueError("库存数量必须大于零")
        sku = await self._updated_sku(
            session,
            update(Sku)
            .where(
                Sku.id == sku_id,
                Sku.locked_stock >= quantity,
                Sku.physical_stock >= quantity,
            )
            .values(
                locked_stock=Sku.locked_stock - quantity,
                physical_stock=Sku.physical_stock - quantity,
            )
            .returning(Sku.id),
            sku_id,
        )
        if sku is None:
            await self._raise_stock_error(session, sku_id)
            raise AssertionError("库存错误分支应已抛出异常")
        await self._ledger(
            session,
            sku,
            InventoryEventType.DEDUCT,
            quantity,
            reference_no,
            request_id,
            physical_before=sku.physical_stock + quantity,
            locked_before=sku.locked_stock + quantity,
        )
        return sku

    async def purchase_in(
        self, session: AsyncSession, sku_id: int, quantity: int, reference_no: str, request_id: str
    ) -> Sku:
        """入库，同时增加实物和可售库存。"""
        if quantity <= 0:
            raise ValueError("库存数量必须大于零")
        sku = await self._updated_sku(
            session,
            update(Sku).where(Sku.id == sku_id).values(physical_stock=Sku.physical_stock + quantity).returning(Sku.id),
            sku_id,
        )
        if sku is None:
            raise InventoryNotFound(f"SKU {sku_id} 不存在")
        await self._ledger(
            session,
            sku,
            InventoryEventType.PURCHASE_IN,
            quantity,
            reference_no,
            request_id,
            physical_before=sku.physical_stock - quantity,
            locked_before=sku.locked_stock,
        )
        return sku

    async def adjust(
        self,
        session: AsyncSession,
        sku_id: int,
        quantity: int,
        reference_no: str,
        request_id: str,
    ) -> Sku:
        """手工调整实物库存，禁止调整后低于锁定库存。"""
        if quantity == 0:
            raise ValueError("调整数量不能为零")
        sku = await self._updated_sku(
            session,
            update(Sku)
            .where(
                Sku.id == sku_id,
                Sku.physical_stock + quantity >= Sku.locked_stock,
                Sku.physical_stock + quantity >= 0,
            )
            .values(physical_stock=Sku.physical_stock + quantity)
            .returning(Sku.id),
            sku_id,
        )
        if sku is None:
            await self._raise_stock_error(session, sku_id)
            raise AssertionError("库存错误分支应已抛出异常")
        await self._ledger(
            session,
            sku,
            InventoryEventType.MANUAL_ADJUST,
            quantity,
            reference_no,
            request_id,
            physical_before=sku.physical_stock - quantity,
            locked_before=sku.locked_stock,
            reason=reference_no,
        )
        return sku

    async def list_stock(self, session: AsyncSession, offset: int, limit: int) -> tuple[list[Sku], int]:
        """后台分页读取 SKU 库存。"""
        result = await session.scalars(select(Sku).order_by(Sku.id).offset(offset).limit(limit))
        total = await session.scalar(select(func.count(Sku.id)))
        return list(result.all()), int(total or 0)

    async def list_ledgers(self, session: AsyncSession, sku_id: int, limit: int = 100) -> list[InventoryLedger]:
        """读取 SKU 最近的库存流水。"""
        result = await session.scalars(
            select(InventoryLedger)
            .where(InventoryLedger.sku_id == sku_id)
            .order_by(InventoryLedger.created_at.desc())
            .limit(limit)
        )
        return list(result.all())
