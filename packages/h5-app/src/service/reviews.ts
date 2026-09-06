import type { ApiEnvelope, ProductReviewResponse } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取商品审核通过的评价。 */
export async function listProductReviews(productId: number): Promise<ProductReviewResponse> {
  const response = await httpClient.get<ApiEnvelope<ProductReviewResponse>>(
    `/reviews/products/${productId}`,
  );
  return response.data.data;
}
