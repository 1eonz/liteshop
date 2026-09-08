import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AdminReviewRecord } from '@liteshop/shared-types';
import {
  auditAdminReview,
  listAdminReviews,
  replyAdminReview,
} from '../../../service/admin/reviews';

/** 后台评价审核查询。 */
export function useAdminReviewsQuery() {
  return useQuery<AdminReviewRecord[]>({
    queryKey: ['admin-reviews'],
    queryFn: listAdminReviews,
  });
}

/** 后台评价审核写操作，禁止自动重试。 */
export function useAdminReviewMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      reviewId,
      status,
      reason,
    }: {
      reviewId: number;
      status: 'APPROVED' | 'REJECTED';
      reason: string;
    }) => auditAdminReview(reviewId, status, reason),
    retry: 0,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin-reviews'] }),
  });
}

/** 后台评价回复写操作，禁止自动重试。 */
export function useAdminReviewReplyMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ reviewId, reply }: { reviewId: number; reply: string }) =>
      replyAdminReview(reviewId, reply),
    retry: 0,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['admin-reviews'] }),
  });
}
