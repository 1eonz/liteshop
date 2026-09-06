"""用户与收货地址仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..errors.domain import AddressNotFound
from ..models.user import Address, User


class UserRepository:
    """封装用户和地址的持久化查询。"""

    async def get_by_phone(self, session: AsyncSession, phone: str) -> User | None:
        """按手机号查找用户。"""
        return cast(User | None, await session.scalar(select(User).where(User.phone == phone)))

    async def get(self, session: AsyncSession, user_id: int) -> User | None:
        """按 ID 查找用户。"""
        return cast(User | None, await session.get(User, user_id))

    async def create(self, session: AsyncSession, phone: str) -> User:
        """创建短信登录用户。"""
        now = datetime.now(UTC)
        user = User(phone=phone, created_at=now, updated_at=now, last_login_at=now)
        session.add(user)
        await session.flush()
        return user

    async def get_or_create_by_phone(self, session: AsyncSession, phone: str) -> User:
        """并发首次登录时通过保存点恢复手机号唯一键冲突。"""
        existing = await self.get_by_phone(session, phone)
        if existing is not None:
            return existing
        try:
            async with session.begin_nested():
                return await self.create(session, phone)
        except IntegrityError:
            # 竞争事务提交后再次查询，外层事务仍保持可继续使用的状态。
            recovered = await self.get_by_phone(session, phone)
            if recovered is None:
                raise
            return recovered

    async def touch_login(self, session: AsyncSession, user: User) -> User:
        """更新最近登录时间。"""
        user.last_login_at = datetime.now(UTC)
        user.updated_at = user.last_login_at
        await session.flush()
        return user

    async def list_addresses(self, session: AsyncSession, user_id: int) -> list[Address]:
        """默认地址优先返回。"""
        result = await session.scalars(
            select(Address)
            .where(Address.user_id == user_id)
            .order_by(Address.is_default.desc(), Address.created_at.desc())
        )
        return list(result.all())

    async def get_address_for_update(self, session: AsyncSession, user_id: int, address_id: int) -> Address:
        """锁定属于当前用户的地址。"""
        address = cast(
            Address | None,
            await session.scalar(
                select(Address).where(Address.id == address_id, Address.user_id == user_id).with_for_update()
            ),
        )
        if address is None:
            raise AddressNotFound(address_id)
        return address

    async def clear_default_address(self, session: AsyncSession, user_id: int) -> None:
        """清除用户原默认地址。"""
        await session.execute(
            update(Address).where(Address.user_id == user_id, Address.is_default.is_(True)).values(is_default=False)
        )

    async def add_address(self, session: AsyncSession, address: Address) -> Address:
        """新增地址，不提交外层事务。"""
        session.add(address)
        await session.flush()
        return address

    async def flush(self, session: AsyncSession) -> None:
        """刷新当前事务，让调用方可以立即读取数据库生成值。"""
        await session.flush()

    async def delete_address(self, session: AsyncSession, address: Address) -> None:
        """删除地址，不提交外层事务。"""
        await session.delete(address)
        await session.flush()
