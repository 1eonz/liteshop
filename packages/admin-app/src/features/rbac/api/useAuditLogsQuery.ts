import { useQuery } from '@tanstack/react-query';
import { listAuditLogs } from '../../../service/admin/access';

/** 失败保留为查询错误，避免将审计服务故障显示为没有记录。 */
export function useAuditLogsQuery() {
  return useQuery({ queryKey: ['admin-audit-logs'], queryFn: listAuditLogs });
}
