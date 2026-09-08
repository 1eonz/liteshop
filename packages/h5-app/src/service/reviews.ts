import type { ApiEnvelope, ProductReviewResponse, ReviewCreateInput } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取商品审核通过的评价。 */
export async function listProductReviews(productId: number): Promise<ProductReviewResponse> {
  const response = await httpClient.get<ApiEnvelope<ProductReviewResponse>>(
    `/reviews/products/${productId}`,
  );
  return response.data.data;
}

/** 提交已完成订单项评价。 */
export async function createReview(
  input: ReviewCreateInput,
): Promise<{ id: number; status: string; rating: number }> {
  const response = await httpClient.post<
    ApiEnvelope<{ id: number; status: string; rating: number }>
  >('/reviews', input);
  return response.data.data;
}
