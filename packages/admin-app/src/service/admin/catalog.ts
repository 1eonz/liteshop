import type {
  ApiEnvelope,
  CategorySummary,
  PageResponse,
  ProductCreateInput,
  ProductDetailResponse,
  ProductSummary,
  ProductUpdateInput,
  AdminProductQuery,
} from '@liteshop/shared-types';
import { httpClient } from '../http';

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

/** 更新后台商品。 */
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
