import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AdminPermission, AdminRole, AdminUserRecord } from '@liteshop/shared-types';
import {
  createAdminRole,
  deleteAdminRole,
  listAdminPermissions,
  listAdminRoles,
  listAdminUsers,
  updateAdminRole,
  updateAdminUserRoles,
} from '../../../service/admin/access';
import { isRecoverableApiError } from '../../../service/http';

/** RBAC 角色与权限查询。 */
export function useRbacQuery() {
  const roles = useQuery<AdminRole[]>({
    queryKey: ['admin-roles'],
    queryFn: async () => {
      try {
        return await listAdminRoles();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
  const permissions = useQuery<AdminPermission[]>({
    queryKey: ['admin-permissions'],
    queryFn: async () => {
      try {
        return await listAdminPermissions();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
  const users = useQuery<AdminUserRecord[]>({
    queryKey: ['admin-users-rbac'],
    queryFn: listAdminUsers,
  });
  return { roles, permissions, users };
}

/** RBAC 写操作集合，统一关闭 mutation 自动重试。 */
export function useRbacMutations() {
  const queryClient = useQueryClient();
  const refresh = (): void => {
    void queryClient.invalidateQueries({ queryKey: ['admin-roles'] });
    void queryClient.invalidateQueries({ queryKey: ['admin-users-rbac'] });
  };
  const create = useMutation({
    mutationFn: ({ name, permissionCodes }: { name: string; permissionCodes: string[] }) =>
      createAdminRole(name, permissionCodes),
    retry: 0,
    onSuccess: refresh,
  });
  const update = useMutation({
    mutationFn: ({
      roleId,
      name,
      permissionCodes,
    }: {
      roleId: number;
      name?: string;
      permissionCodes?: string[];
    }) => updateAdminRole(roleId, { name, permissionCodes }),
    retry: 0,
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: deleteAdminRole,
    retry: 0,
    onSuccess: refresh,
  });
  const updateUserRoles = useMutation({
    mutationFn: ({ userId, roleIds }: { userId: number; roleIds: number[] }) =>
      updateAdminUserRoles(userId, roleIds),
    retry: 0,
    onSuccess: refresh,
  });
  return { create, update, remove, updateUserRoles };
}
