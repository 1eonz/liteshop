import { useQuery } from '@tanstack/react-query';
import type { AdminPermission, AdminRole } from '@liteshop/shared-types';
import { listAdminPermissions, listAdminRoles } from '../../../service/admin/access';
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
  return { roles, permissions };
}
