import { useQuery } from '@tanstack/react-query';
import type { DashboardData } from '@liteshop/shared-types';
import { getDashboard } from '../../../service/admin/settings';

/** 后台看板聚合查询。 */
export function useDashboardQuery() {
  return useQuery<DashboardData>({ queryKey: ['admin-dashboard'], queryFn: getDashboard });
}
