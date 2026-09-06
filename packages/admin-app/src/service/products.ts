import type { ApiEnvelope, PageResponse, ProductSummary } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface ProductListQuery {
  page?: number;
  pageSize?: number;
  q?: string;
}

/** 后台商品 API 管理层，页面和组件禁止直接发起 HTTP 请求。 */
export async function listProducts(
  query: ProductListQuery = {},
): Promise<PageResponse<ProductSummary>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<ProductSummary>>>('/products', {
    params: query,
  });
  return response.data.data;
}
