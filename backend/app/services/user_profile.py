"""用户资料与收货地址业务服务。"""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import Address, User
from ..repositories.user import UserRepository
from ..schemas.users import AddressCreate, AddressUpdate


class UserProfileNotFound(KeyError):
    """用户资料不存在。"""


class UserProfileService:
    """编排用户资料和收货地址用例。"""

    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    @staticmethod
    def profile_response(user: User) -> dict[str, object]:
        """把用户实体转换为 API 字段。"""
        return {
            "id": user.id,
            "phone": user.phone,
            "nickname": user.nickname,
            "avatar": user.avatar,
            "gender": user.gender,
            "status": user.status,
            "birthday": user.birthday.isoformat() if user.birthday is not None else None,
            "lastLoginAt": user.last_login_at.isoformat() if user.last_login_at is not None else None,
            "createdAt": user.created_at.isoformat(),
            "updatedAt": user.updated_at.isoformat(),
        }

    @staticmethod
    def address_response(address: Address) -> dict[str, object]:
        """把地址实体转换为 API 字段。"""
        return {
            "id": address.id,
            "receiverName": address.receiver_name,
            "phone": address.phone,
            "provinceCode": address.province_code,
            "cityCode": address.city_code,
            "districtCode": address.district_code,
            "detail": address.detail,
            "isDefault": address.is_default,
            "createdAt": address.created_at.isoformat(),
            "updatedAt": address.updated_at.isoformat(),
        }

    async def get_profile(self, session: AsyncSession, user_id: int) -> dict[str, object]:
        """读取当前用户资料。"""
        user = await self.repository.get(session, user_id)
        if user is None:
            raise UserProfileNotFound(user_id)
        return self.profile_response(user)

    async def list_addresses(self, session: AsyncSession, user_id: int) -> list[dict[str, object]]:
        """按默认优先顺序读取收货地址。"""
        addresses = await self.repository.list_addresses(session, user_id)
        return [self.address_response(address) for address in addresses]

    async def create_address(
        self,
        session: AsyncSession,
        user_id: int,
        payload: AddressCreate,
    ) -> dict[str, object]:
        """创建收货地址，首个地址自动设为默认。"""
        existing = await self.repository.list_addresses(session, user_id)
        make_default = payload.is_default or not existing
        if make_default:
            await self.repository.clear_default_address(session, user_id)
        now = datetime.now(UTC)
        address = await self.repository.add_address(
            session,
            Address(
                user_id=user_id,
                receiver_name=payload.receiver_name,
                phone=payload.phone,
                province_code=payload.province_code,
                city_code=payload.city_code,
                district_code=payload.district_code,
                detail=payload.detail,
                is_default=make_default,
                created_at=now,
                updated_at=now,
            ),
        )
        return self.address_response(address)

    async def update_address(
        self,
        session: AsyncSession,
        user_id: int,
        address_id: int,
        payload: AddressUpdate,
    ) -> dict[str, object]:
        """更新地址并在需要时重新设置默认地址。"""
        address = await self.repository.get_address_for_update(session, user_id, address_id)
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        make_default = changes.pop("is_default", None)
        if make_default is True:
            await self.repository.clear_default_address(session, user_id)
            address.is_default = True
        elif make_default is False and address.is_default:
            addresses = await self.repository.list_addresses(session, user_id)
            address.is_default = False
            replacement = next((item for item in addresses if item.id != address_id), None)
            if replacement is not None:
                replacement.is_default = True
        for field, value in changes.items():
            if value is not None:
                setattr(address, field, value)
        address.updated_at = datetime.now(UTC)
        await self.repository.flush(session)
        return self.address_response(address)

    async def delete_address(self, session: AsyncSession, user_id: int, address_id: int) -> None:
        """删除地址并为剩余地址补选默认地址。"""
        address = await self.repository.get_address_for_update(session, user_id, address_id)
        was_default = address.is_default
        await self.repository.delete_address(session, address)
        if was_default:
            remaining = await self.repository.list_addresses(session, user_id)
            if remaining:
                remaining[0].is_default = True
                remaining[0].updated_at = datetime.now(UTC)
                await self.repository.flush(session)


user_profile_service = UserProfileService()
