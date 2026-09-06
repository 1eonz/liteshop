import type {
  ApiEnvelope,
  DashboardData,
  FreightTemplate,
  InventoryRow,
  OrderDetail,
  PageResponse,
  ProductDetailResponse,
  ProductCreateInput,
  ProductUpdateInput,
  ProductSummary,
  AdminProductQuery,
  ShipOrderInput,
  OrderManagementInput,
  AdminPermission,
  AdminRole,
  AuditLogEntry,
  CategorySummary,
  MemberDetail,
  MemberSummary,
} from '@liteshop/shared-types';
import { httpClient } from './http';

/** 后台商品列表。 */
export async function listAdminProducts(
  query: AdminProductQuery = {},
): Promise<PageResponse<ProductSummary>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<ProductSummary>>>(
    '/admin/products',
    { params: query },
  );
  return response.data.data;
}

/** 后台商品详情。 */
export async function getAdminProduct(productId: number): Promise<ProductDetailResponse> {
  const response = await httpClient.get<ApiEnvelope<ProductDetailResponse>>(
    `/products/${productId}`,
  );
  return response.data.data;
}

export async function updateAdminProduct(
  productId: number,
  input: ProductUpdateInput,
): Promise<ProductDetailResponse> {
  const response = await httpClient.put<ApiEnvelope<ProductDetailResponse>>(
    `/admin/products/${productId}`,
    input,
  );
  return response.data.data;
}

/** 创建后台商品，SPU 与首个 SKU 在同一请求中提交。 */
export async function createAdminProduct(
  input: ProductCreateInput,
): Promise<ProductDetailResponse> {
  const response = await httpClient.post<ApiEnvelope<ProductDetailResponse>>(
    '/admin/products',
    input,
  );
  return response.data.data;
}

export async function listAdminOrders(page = 1, pageSize = 20): Promise<PageResponse<OrderDetail>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<OrderDetail>>>('/admin/orders', {
    params: { page, pageSize },
  });
  return response.data.data;
}

export async function shipAdminOrder(orderId: number, input: ShipOrderInput): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/ship`,
    input,
  );
  return response.data.data;
}

export async function listInventory(page = 1, pageSize = 50): Promise<PageResponse<InventoryRow>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<InventoryRow>>>(
    '/admin/inventory',
    { params: { page, pageSize } },
  );
  return response.data.data;
}

export async function adjustInventory(
  skuId: number,
  quantity: number,
  reason: string,
): Promise<InventoryRow> {
  const response = await httpClient.post<ApiEnvelope<InventoryRow>>(
    `/admin/inventory/${skuId}/adjust`,
    { quantity, reason },
  );
  return response.data.data;
}

export async function getDashboard(): Promise<DashboardData> {
  const response = await httpClient.get<ApiEnvelope<DashboardData>>('/admin/dashboard');
  return response.data.data;
}

export async function listFreightTemplates(): Promise<FreightTemplate[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: FreightTemplate[] }>>(
    '/admin/freight-templates',
  );
  return response.data.data.items;
}

/** 后台分类列表。 */
export async function listAdminCategories(): Promise<CategorySummary[]> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: CategorySummary[] }>>('/admin/categories');
  return response.data.data.items;
}

/** 创建后台分类。 */
export async function createAdminCategory(input: {
  name: string;
  parentId?: number | null;
  icon?: string;
  sortOrder?: number;
}): Promise<CategorySummary> {
  const response = await httpClient.post<ApiEnvelope<CategorySummary>>('/admin/categories', input);
  return response.data.data;
}

/** 更新后台分类。 */
export async function updateAdminCategory(
  categoryId: number,
  input: Partial<CategorySummary>,
): Promise<CategorySummary> {
  const response = await httpClient.put<ApiEnvelope<CategorySummary>>(
    `/admin/categories/${categoryId}`,
    input,
  );
  return response.data.data;
}

/** 停用后台分类。 */
export async function deleteAdminCategory(categoryId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ deleted: boolean }>>(`/admin/categories/${categoryId}`);
}

/** 取消后台订单。 */
export async function cancelAdminOrder(orderId: number): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/cancel`,
  );
  return response.data.data;
}

/** 更新后台订单备注或地址。 */
export async function updateAdminOrder(
  orderId: number,
  input: OrderManagementInput,
): Promise<OrderDetail> {
  const response = await httpClient.put<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}`,
    input,
  );
  return response.data.data;
}

/** 修改待付款订单金额。 */
export async function changeAdminOrderPrice(
  orderId: number,
  totalAmount: number,
): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/price`,
    { totalAmount },
  );
  return response.data.data;
}

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

/** 读取后台会员分页列表。 */
export async function listMembers(page = 1, pageSize = 20): Promise<PageResponse<MemberSummary>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<MemberSummary>>>(
    '/admin/members',
    {
      params: { page, pageSize },
    },
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

/** 读取 SKU 库存流水。 */
export async function listInventoryLedger(
  skuId: number,
): Promise<import('@liteshop/shared-types').InventoryLedgerEntry[]> {
  const response = await httpClient.get<
    ApiEnvelope<{
      items: import('@liteshop/shared-types').InventoryLedgerEntry[];
    }>
  >(`/admin/inventory/${skuId}/ledger`);
  return response.data.data.items;
}

/** 读取商城主题配置。 */
export async function getThemeSettings(): Promise<{
  primaryColor: string;
  navigationStyle: string;
  tabbarStyle: string;
}> {
  const response = await httpClient.get<
    ApiEnvelope<{
      primaryColor: string;
      navigationStyle: string;
      tabbarStyle: string;
    }>
  >('/settings/theme');
  return response.data.data;
}

/** 更新商城主题配置。 */
export async function updateThemeSettings(input: {
  primaryColor: string;
  navigationStyle: string;
  tabbarStyle: string;
}): Promise<{
  primaryColor: string;
  navigationStyle: string;
  tabbarStyle: string;
}> {
  const response = await httpClient.put<
    ApiEnvelope<{
      primaryColor: string;
      navigationStyle: string;
      tabbarStyle: string;
    }>
  >('/settings/theme', input);
  return response.data.data;
}

/** 读取一期功能开关。 */
export async function listFeatureFlags(): Promise<Array<{ key: string; enabled: boolean }>> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: Array<{ key: string; enabled: boolean }> }>>(
      '/settings/feature-flags',
    );
  return response.data.data.items;
}
