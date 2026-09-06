import type {
  ApiEnvelope,
  CategorySummary,
  PageResponse,
  ProductDetailResponse,
  ProductListQuery,
  ProductSummary,
} from '@liteshop/shared-types';
import { httpClient } from './http';

/** 商品 API 管理层，页面和组件禁止直接发起 HTTP 请求。 */
export async function listProducts(
  query: ProductListQuery = {},
): Promise<PageResponse<ProductSummary>> {
  const path = query.q ? '/products/search' : '/products';
  const response = await httpClient.get<ApiEnvelope<PageResponse<ProductSummary>>>(path, {
    params: query,
  });
  return response.data.data;
}

/** 获取商品详情和可售 SKU。 */
export async function getProduct(productId: number): Promise<ProductDetailResponse> {
  const response = await httpClient.get<ApiEnvelope<ProductDetailResponse>>(
    `/products/${productId}`,
  );
  return response.data.data;
}

/** 读取商城分类树。 */
export async function listCategories(): Promise<CategorySummary[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: CategorySummary[] }>>('/categories');
  return response.data.data.items;
}
