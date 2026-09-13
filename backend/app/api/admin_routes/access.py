"""管理后台看板、审计和 RBAC 路由。"""

from fastapi import APIRouter, Header
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.admin import RoleCreate, RoleUpdate, UserRolesUpdate
from ..dependencies import CurrentSubject
from ..responses import success
from .common import admin_service, authorize_read, execute_write, require_database, session_dependency

router = APIRouter()


@router.get("/dashboard")
async def dashboard(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """返回核心指标、趋势和商品排行。"""
    require_database()
    await authorize_read(session, subject, "dashboard.read")
    return success(await admin_service.dashboard(session))


@router.get("/audit-logs")
async def audit_logs(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """返回最近后台操作日志。"""
    require_database()
    await authorize_read(session, subject, "audit.read")
    return success({"items": await admin_service.audit_logs(session)})


@router.get("/roles")
async def list_roles(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """读取 RBAC 角色列表。"""
    require_database()
    await authorize_read(session, subject, "rbac.read")
    return success({"items": await admin_service.list_roles(session)})


@router.get("/permissions")
async def list_permissions(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """读取 RBAC 权限点列表。"""
    require_database()
    await authorize_read(session, subject, "rbac.read")
    return success({"items": await admin_service.list_permissions(session)})


@router.get("/users")
async def list_users_with_roles(
    subject: CurrentSubject, session: AsyncSession = session_dependency
) -> dict[str, object]:
    """读取管理员角色分配列表。"""
    require_database()
    await authorize_read(session, subject, "rbac.read")
    return success({"items": await admin_service.list_users_with_roles(session)})


@router.post("/roles")
async def create_role(
    payload: RoleCreate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """创建后台角色。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type="admin_role_create",
        permission="rbac.write",
        resource_type="role",
        operation=lambda session, user_id, request_id: admin_service.create_role(session, payload, user_id, request_id),
    )


@router.put("/roles/{role_id}")
async def update_role(
    role_id: int, payload: RoleUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """更新后台角色。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_role_update:{role_id}",
        permission="rbac.write",
        resource_type="role",
        operation=lambda session, user_id, request_id: admin_service.update_role(
            session, role_id, payload, user_id, request_id
        ),
    )


@router.delete("/roles/{role_id}")
async def delete_role(role_id: int, subject: CurrentSubject, x_request_id: str = Header(...)) -> dict[str, object]:
    """删除未绑定管理员的后台角色。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_role_delete:{role_id}",
        permission="rbac.write",
        resource_type="role",
        operation=lambda session, user_id, request_id: admin_service.delete_role(session, role_id, user_id, request_id),
    )


@router.put("/users/{user_id}/roles")
async def update_user_roles(
    user_id: int, payload: UserRolesUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """覆盖管理员的角色绑定。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_user_roles:{user_id}",
        permission="rbac.write",
        resource_type="user_role",
        operation=lambda session, operator_id, request_id: admin_service.update_user_roles(
            session, user_id, payload, operator_id, request_id
        ),
    )
