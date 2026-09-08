import type { AdminReviewRecord, ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 读取后台待审核评价。 */
export async function listAdminReviews(): Promise<AdminReviewRecord[]> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: AdminReviewRecord[] }>>('/admin/reviews');
  return response.data.data.items;
}

/** 更新评价审核状态。 */
export async function auditAdminReview(
  reviewId: number,
  status: 'APPROVED' | 'REJECTED',
  reason: string,
): Promise<{ id: number; status: string; reason: string | null }> {
  const response = await httpClient.put<
    ApiEnvelope<{ id: number; status: string; reason: string | null }>
  >(`/admin/reviews/${reviewId}`, { status, reason });
  return response.data.data;
}

/** 保存已通过评价的商家回复。 */
export async function replyAdminReview(
  reviewId: number,
  reply: string,
): Promise<{ id: number; merchantReply: string; merchantRepliedAt: string }> {
  const response = await httpClient.put<
    ApiEnvelope<{ id: number; merchantReply: string; merchantRepliedAt: string }>
  >(`/admin/reviews/${reviewId}/reply`, { reply });
  return response.data.data;
}
