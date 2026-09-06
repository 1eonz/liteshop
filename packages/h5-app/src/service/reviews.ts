import type { ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface ProductReviewItem {
  id: number;
  rating: number;
  content: string;
  images: string[];
  createdAt: string;
}

export interface ProductReviewResponse {
  averageRating: number;
  items: ProductReviewItem[];
}

/** 读取商品审核通过的评价。 */
export async function listProductReviews(productId: number): Promise<ProductReviewResponse> {
  const response = await httpClient.get<ApiEnvelope<ProductReviewResponse>>(
    `/reviews/products/${productId}`,
  );
  return response.data.data;
}
