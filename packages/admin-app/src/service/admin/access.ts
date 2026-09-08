import type {
  AdminPermission,
  AdminRole,
  AdminUserRecord,
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

/** 读取管理员角色绑定快照。 */
export async function listAdminUsers(): Promise<AdminUserRecord[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: AdminUserRecord[] }>>('/admin/users');
  return response.data.data.items;
}

/** 创建后台角色。 */
export async function createAdminRole(name: string, permissionCodes: string[]): Promise<AdminRole> {
  const response = await httpClient.post<ApiEnvelope<AdminRole>>('/admin/roles', {
    name,
    permissionCodes,
  });
  return response.data.data;
}

/** 更新后台角色。 */
export async function updateAdminRole(
  roleId: number,
  input: { name?: string; permissionCodes?: string[] },
): Promise<AdminRole> {
  const response = await httpClient.put<ApiEnvelope<AdminRole>>(`/admin/roles/${roleId}`, input);
  return response.data.data;
}

/** 删除后台角色。 */
export async function deleteAdminRole(roleId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ deleted: boolean }>>(`/admin/roles/${roleId}`);
}

/** 覆盖管理员角色绑定。 */
export async function updateAdminUserRoles(
  userId: number,
  roleIds: number[],
): Promise<AdminUserRecord> {
  const response = await httpClient.put<ApiEnvelope<AdminUserRecord>>(
    `/admin/users/${userId}/roles`,
    { roleIds },
  );
  return response.data.data;
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
