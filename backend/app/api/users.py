"""用户资料与收货地址 HTTP 适配层。"""

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import get_session
from ..errors import ApiError
from ..errors.domain import AddressNotFound
from ..schemas.users import AddressCreate, AddressUpdate
from ..services.idempotency import IdempotencyInProgress, IdempotentResult, idempotency_service
from ..services.user_profile import UserProfileNotFound, user_profile_service
from .dependencies import CurrentSubject
from .responses import success

router = APIRouter(prefix="/user", tags=["user"])
_session_dependency = Depends(get_session)
_memory_addresses: dict[str, list[dict[str, object]]] = {}
_memory_address_id = 0


def _memory_profile(subject: str) -> dict[str, object]:
    """构造开发模式下的最小用户资料。"""
    return {
        "id": subject,
        "phone": subject,
        "nickname": "",
        "avatar": "",
        "gender": "UNKNOWN",
        "status": "ACTIVE",
        "birthday": None,
        "lastLoginAt": None,
        "createdAt": "",
        "updatedAt": "",
    }


def _database_user_id(subject: str) -> int:
    """校验当前环境和数据库用户主体。"""
    if not settings.use_database:
        raise ApiError(
            status_code=503,
            code=50001,
            i18n_key="common.internal_error",
            message="用户资料服务需要本地数据库",
        )
    try:
        return int(subject)
    except ValueError as error:
        raise ApiError(
            status_code=401,
            code=40101,
            i18n_key="auth.unauthorized",
            message="用户身份无效",
        ) from error


@router.get("/me")
async def get_profile(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取当前登录用户资料。"""
    if not settings.use_database:
        return success(_memory_profile(subject))
    try:
        return success(await user_profile_service.get_profile(session, _database_user_id(subject)))
    except UserProfileNotFound as error:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="用户不存在",
        ) from error


@router.get("/addresses")
async def list_addresses(
    subject: CurrentSubject,
    session: AsyncSession = _session_dependency,
) -> dict[str, object]:
    """读取当前用户的收货地址。"""
    if not settings.use_database:
        return success({"items": list(_memory_addresses.get(subject, []))})
    return success({"items": await user_profile_service.list_addresses(session, _database_user_id(subject))})


@router.post("/addresses")
async def create_address(
    payload: AddressCreate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等创建当前用户的收货地址。"""
    if not settings.use_database:

        async def memory_operation(_session: AsyncSession | None) -> IdempotentResult:
            global _memory_address_id
            _memory_address_id += 1
            addresses = _memory_addresses.setdefault(subject, [])
            should_default = payload.is_default or not addresses
            if should_default:
                for address in addresses:
                    address["isDefault"] = False
            address = {
                "id": _memory_address_id,
                "receiverName": payload.receiver_name,
                "phone": payload.phone,
                "provinceCode": payload.province_code,
                "cityCode": payload.city_code,
                "districtCode": payload.district_code,
                "detail": payload.detail,
                "isDefault": should_default,
                "createdAt": "",
                "updatedAt": "",
            }
            addresses.append(address)
            return IdempotentResult(address, "address", str(_memory_address_id))

        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type="address_create",
            operation=memory_operation,
        )
        return success(result)

    user_id = _database_user_id(subject)

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        address = await user_profile_service.create_address(session, user_id, payload)
        return IdempotentResult(address, "address", str(address["id"]))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type="address_create",
            operation=operation,
        )
        return success(result)
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.put("/addresses/{address_id}")
async def update_address(
    address_id: int,
    payload: AddressUpdate,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等更新当前用户地址。"""
    if not settings.use_database:

        async def memory_operation(_session: AsyncSession | None) -> IdempotentResult:
            addresses = _memory_addresses.setdefault(subject, [])
            address = next((item for item in addresses if item["id"] == address_id), None)
            if address is None:
                raise AddressNotFound(address_id)
            changes = payload.model_dump(exclude_unset=True, by_alias=True)
            if changes.get("isDefault") is True:
                for item in addresses:
                    item["isDefault"] = False
                address["isDefault"] = True
            elif changes.get("isDefault") is False and address.get("isDefault") is True:
                address["isDefault"] = False
                replacement = next((item for item in addresses if item["id"] != address_id), None)
                if replacement is not None:
                    replacement["isDefault"] = True
            for field, value in changes.items():
                if field != "isDefault" and value is not None:
                    address[field] = value
            return IdempotentResult(address, "address", str(address_id))

        try:
            result = await idempotency_service.execute(
                user_id=subject,
                request_id=x_request_id,
                action_type=f"address_update:{address_id}",
                operation=memory_operation,
            )
            return success(result)
        except AddressNotFound as error:
            raise ApiError(
                status_code=404, code=40401, i18n_key="common.not_found", message="收货地址不存在"
            ) from error

    user_id = _database_user_id(subject)

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        address = await user_profile_service.update_address(session, user_id, address_id, payload)
        return IdempotentResult(address, "address", str(address_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"address_update:{address_id}",
            operation=operation,
        )
        return success(result)
    except AddressNotFound as error:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="收货地址不存在",
        ) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: int,
    subject: CurrentSubject,
    x_request_id: str = Header(...),
) -> dict[str, object]:
    """幂等删除当前用户地址。"""
    if not settings.use_database:

        async def memory_operation(_session: AsyncSession | None) -> IdempotentResult:
            addresses = _memory_addresses.setdefault(subject, [])
            index = next((position for position, item in enumerate(addresses) if item["id"] == address_id), None)
            if index is None:
                raise AddressNotFound(address_id)
            was_default = bool(addresses[index].get("isDefault"))
            addresses.pop(index)
            if was_default and addresses:
                addresses[0]["isDefault"] = True
            return IdempotentResult({"deleted": True, "addressId": address_id}, "address", str(address_id))

        try:
            result = await idempotency_service.execute(
                user_id=subject,
                request_id=x_request_id,
                action_type=f"address_delete:{address_id}",
                operation=memory_operation,
            )
            return success(result)
        except AddressNotFound as error:
            raise ApiError(
                status_code=404, code=40401, i18n_key="common.not_found", message="收货地址不存在"
            ) from error

    user_id = _database_user_id(subject)

    async def operation(session: AsyncSession | None) -> IdempotentResult:
        if session is None:
            raise RuntimeError("数据库事务会话未初始化")
        await user_profile_service.delete_address(session, user_id, address_id)
        return IdempotentResult({"deleted": True, "addressId": address_id}, "address", str(address_id))

    try:
        result = await idempotency_service.execute(
            user_id=subject,
            request_id=x_request_id,
            action_type=f"address_delete:{address_id}",
            operation=operation,
        )
        return success(result)
    except AddressNotFound as error:
        raise ApiError(
            status_code=404,
            code=40401,
            i18n_key="common.not_found",
            message="收货地址不存在",
        ) from error
    except IdempotencyInProgress as error:
        raise ApiError(
            status_code=429,
            code=42901,
            i18n_key="common.request_in_progress",
            message="请求正在处理中，请稍后再试",
        ) from error
