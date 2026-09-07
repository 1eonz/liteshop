/**
 * 历史聚合 Hook 兼容出口。
 * 新代码按领域从各 features 模块的 api 目录导入，避免跨领域状态集中在单文件中。
 */
export * from '../features/catalog/api/useAdminCatalogQueries';
export * from '../features/categories/api/useCategoryQueries';
export * from '../features/dashboard/api/useDashboardQuery';
export * from '../features/inventory/api/useInventoryQueries';
export * from '../features/members/api/useMemberQueries';
export * from '../features/orders/api/useAdminOrderQueries';
export * from '../features/rbac/api/useRbacQuery';

import { useQuery } from '@tanstack/react-query';
import type { AuditLogEntry } from '@liteshop/shared-types';
import { listAuditLogs } from '../service/admin/access';
import { isRecoverableApiError } from '../service/http';

/** 后台操作日志查询，保留兼容入口。 */
export function useAuditLogsQuery() {
  return useQuery<AuditLogEntry[]>({
    queryKey: ['admin-audit-logs'],
    queryFn: async () => {
      try {
        return await listAuditLogs();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
}
