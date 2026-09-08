"""后台 RBAC 写管理的边界测试。"""

import asyncio
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.admin import AdminRepository
from app.schemas.admin import RoleCreate, UserRolesUpdate
from app.services.admin import AdminService


def _service(repository: SimpleNamespace) -> AdminService:
    """注入最小 RBAC 仓储替身。"""
    service = AdminService()
    service.repository = cast(AdminRepository, repository)
    return service


def test_create_role_rejects_unknown_permission() -> None:
    """角色不能绑定不存在的权限点。"""
    repository = SimpleNamespace(
        get_role_by_name=AsyncMock(return_value=None),
        get_permissions_by_codes=AsyncMock(return_value=[]),
    )
    service = _service(repository)
    with pytest.raises(ValueError, match="不存在的权限点"):
        asyncio.run(
            service.create_role(
                cast(AsyncSession, AsyncMock()),
                RoleCreate(name="运营", permissionCodes=["product.read"]),
                "1",
                "request-role",
            )
        )


def test_user_cannot_remove_own_rbac_write_permission() -> None:
    """操作者不能通过角色分配把自己锁在权限管理之外。"""
    user = SimpleNamespace(id=1, nickname="管理员", phone="13800000000", roles=[])
    role = SimpleNamespace(id=2, permissions=[SimpleNamespace(code="product.read")])
    repository = SimpleNamespace(
        get_user_with_roles=AsyncMock(return_value=user),
        list_roles_by_ids=AsyncMock(return_value=[role]),
    )
    service = _service(repository)
    with pytest.raises(ValueError, match="最后的权限管理能力"):
        asyncio.run(
            service.update_user_roles(
                cast(AsyncSession, AsyncMock()),
                1,
                UserRolesUpdate(roleIds=[2]),
                "1",
                "request-user-role",
            )
        )


def test_delete_role_rejects_assigned_role() -> None:
    """仍绑定管理员的角色不能删除。"""
    role = SimpleNamespace(id=3, name="客服", permissions=[])
    repository = SimpleNamespace(
        get_role=AsyncMock(return_value=role),
        count_role_users=AsyncMock(return_value=1),
    )
    service = _service(repository)
    with pytest.raises(ValueError, match="仍绑定管理员"):
        asyncio.run(
            service.delete_role(
                cast(AsyncSession, AsyncMock()),
                3,
                "1",
                "request-role-delete",
            )
        )
