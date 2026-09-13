"""管理后台 RBAC、审计与数据看板领域服务。"""

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.user import Role
from ..schemas.admin import RoleCreate, RoleUpdate, UserRolesUpdate
from .admin_core import AdminServiceCore


class AdminAccessService(AdminServiceCore):
    """编排后台权限、审计日志和数据看板查询。"""

    async def dashboard(self, session: AsyncSession) -> dict[str, object]:
        """读取数据看板聚合。"""
        return await self.repository.dashboard(session)

    async def audit_logs(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回结构化操作日志。"""
        logs = await self.repository.list_audit_logs(session)
        return [
            {
                "id": log.id,
                "adminId": log.admin_id,
                "resourceType": log.resource_type,
                "resourceId": log.resource_id,
                "action": log.action,
                "requestId": log.request_id,
                "beforeData": log.before_data,
                "afterData": log.after_data,
                "ip": log.ip,
                "userAgent": log.user_agent,
                "createdAt": log.created_at.isoformat(),
            }
            for log in logs
        ]

    async def list_roles(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回角色及权限点，供后台 RBAC 页面展示。"""
        roles = await self.repository.list_roles(session)
        return [
            {"id": role.id, "name": role.name, "permissions": [permission.code for permission in role.permissions]}
            for role in roles
        ]

    async def list_permissions(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回系统权限点。"""
        permissions = await self.repository.list_permissions(session)
        return [{"id": permission.id, "code": permission.code} for permission in permissions]

    async def list_users_with_roles(self, session: AsyncSession) -> list[dict[str, object]]:
        """返回管理员角色分配页面所需的最小用户快照。"""
        users = await self.repository.list_users_with_roles(session)
        return [
            {
                "id": user.id,
                "nickname": user.nickname,
                "phone": user.phone,
                "roleIds": [role.id for role in user.roles],
            }
            for user in users
        ]

    @staticmethod
    def _role_response(role: Role) -> dict[str, object]:
        """把角色 ORM 转为后台契约响应。"""
        return {"id": role.id, "name": role.name, "permissions": [permission.code for permission in role.permissions]}

    async def create_role(
        self, session: AsyncSession, payload: RoleCreate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """创建角色并记录审计日志。"""
        name = payload.name.strip()
        if await self.repository.get_role_by_name(session, name) is not None:
            raise ValueError("角色名称已存在")
        permissions = await self.repository.get_permissions_by_codes(
            session, list(dict.fromkeys(payload.permission_codes))
        )
        if len(permissions) != len(set(payload.permission_codes)):
            raise ValueError("包含不存在的权限点")
        role = Role(name=name, permissions=permissions)
        await self.repository.add_role(session, role)
        response = self._role_response(role)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role.id,
            action="CREATE",
            request_id=request_id,
            before_data=None,
            after_data=response,
        )
        return response

    async def update_role(
        self, session: AsyncSession, role_id: int, payload: RoleUpdate, user_id: str, request_id: str
    ) -> dict[str, object]:
        """更新角色名称和权限绑定。"""
        role = await self.repository.get_role(session, role_id, for_update=True)
        if role is None:
            raise ValueError("角色不存在")
        before = self._role_response(role)
        changes = payload.model_dump(exclude_unset=True, by_alias=False)
        if "name" in changes and changes["name"] is not None:
            name = str(changes["name"]).strip()
            duplicate = await self.repository.get_role_by_name(session, name)
            if duplicate is not None and duplicate.id != role_id:
                raise ValueError("角色名称已存在")
            role.name = name
        if "permission_codes" in changes and changes["permission_codes"] is not None:
            codes = list(dict.fromkeys(str(code) for code in changes["permission_codes"]))
            permissions = await self.repository.get_permissions_by_codes(session, codes)
            if len(permissions) != len(set(codes)):
                raise ValueError("包含不存在的权限点")
            if user_id.isdigit():
                operator = await self.repository.get_user_with_roles(session, int(user_id), for_update=True)
                if operator is not None and any(item.id == role_id for item in operator.roles):
                    other_codes = {
                        permission.code
                        for assigned_role in operator.roles
                        if assigned_role.id != role_id
                        for permission in assigned_role.permissions
                    }
                    if "rbac.write" not in set(codes) | other_codes:
                        raise ValueError("不能移除自己最后的权限管理能力")
            role.permissions = permissions
        await self.repository.flush(session)
        response = self._role_response(role)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role.id,
            action="UPDATE",
            request_id=request_id,
            before_data=before,
            after_data=response,
        )
        return response

    async def delete_role(
        self, session: AsyncSession, role_id: int, user_id: str, request_id: str
    ) -> dict[str, object]:
        """删除未分配给管理员的角色，避免权限悬挂。"""
        role = await self.repository.get_role(session, role_id, for_update=True)
        if role is None:
            raise ValueError("角色不存在")
        if await self.repository.count_role_users(session, role_id):
            raise ValueError("角色仍绑定管理员，不能删除")
        before = self._role_response(role)
        await self.repository.delete_role(session, role)
        await self.audit(
            session,
            user_id=user_id,
            resource_type="ROLE",
            resource_id=role_id,
            action="DELETE",
            request_id=request_id,
            before_data=before,
            after_data={"deleted": True},
        )
        return {"deleted": True, "roleId": role_id}

    async def update_user_roles(
        self, session: AsyncSession, user_id: int, payload: UserRolesUpdate, operator_id: str, request_id: str
    ) -> dict[str, object]:
        """覆盖管理员角色集合并写入审计记录。"""
        user = await self.repository.get_user_with_roles(session, user_id, for_update=True)
        if user is None:
            raise ValueError("管理员不存在")
        role_ids = list(dict.fromkeys(payload.role_ids))
        roles = await self.repository.list_roles_by_ids(session, role_ids)
        if len(roles) != len(role_ids):
            raise ValueError("包含不存在的角色")
        if operator_id.isdigit() and int(operator_id) == user_id:
            retained_codes = {permission.code for role in roles for permission in role.permissions}
            if "rbac.write" not in retained_codes:
                raise ValueError("不能移除自己最后的权限管理能力")
        before = {"userId": user.id, "roleIds": [role.id for role in user.roles]}
        user.roles = roles
        await self.repository.flush(session)
        response = {
            "id": user.id,
            "nickname": user.nickname,
            "phone": user.phone,
            "roleIds": [role.id for role in user.roles],
        }
        await self.audit(
            session,
            user_id=operator_id,
            resource_type="USER_ROLE",
            resource_id=user.id,
            action="UPDATE",
            request_id=request_id,
            before_data=before,
            after_data=response,
        )
        return response
