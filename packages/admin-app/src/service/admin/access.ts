import type {
  AdminPermission,
  AdminRole,
  ApiEnvelope,
  AuditLogEntry,
  MemberDetail,
  MemberSummary,
  PageResponse,
} from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 读取后台操作日志。 */
export async function listAuditLogs(): Promise<AuditLogEntry[]> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: AuditLogEntry[] }>>('/admin/audit-logs');
  return response.data.data.items;
}

/** 读取 RBAC 角色。 */
export async function listAdminRoles(): Promise<AdminRole[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: AdminRole[] }>>('/admin/roles');
  return response.data.data.items;
}

/** 读取 RBAC 权限点。 */
export async function listAdminPermissions(): Promise<AdminPermission[]> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: AdminPermission[] }>>('/admin/permissions');
  return response.data.data.items;
}

/** 读取会员分页列表。 */
export async function listMembers(page = 1, pageSize = 20): Promise<PageResponse<MemberSummary>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<MemberSummary>>>(
    '/admin/members',
    { params: { page, pageSize } },
  );
  return response.data.data;
}

/** 读取会员详情。 */
export async function getMember(userId: number): Promise<MemberDetail> {
  const response = await httpClient.get<ApiEnvelope<MemberDetail>>(`/admin/members/${userId}`);
  return response.data.data;
}

/** 更新会员标签。 */
export async function updateMemberTags(
  userId: number,
  tags: string[],
): Promise<{ userId: number; tags: string[] }> {
  const response = await httpClient.put<ApiEnvelope<{ userId: number; tags: string[] }>>(
    `/admin/members/${userId}/tags`,
    { tags },
  );
  return response.data.data;
}

/** 更新会员等级。 */
export async function updateMemberLevel(
  userId: number,
  memberLevel: 'NORMAL' | 'MEMBER',
): Promise<{ userId: number; memberLevel: 'NORMAL' | 'MEMBER' }> {
  const response = await httpClient.put<
    ApiEnvelope<{ userId: number; memberLevel: 'NORMAL' | 'MEMBER' }>
  >(`/admin/members/${userId}/level`, { memberLevel });
  return response.data.data;
}
