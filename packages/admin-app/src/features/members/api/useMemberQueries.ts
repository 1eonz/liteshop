import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { MemberDetail, MemberSummary, PageResponse } from '@liteshop/shared-types';
import {
  getMember,
  listMembers,
  updateMemberLevel,
  updateMemberTags,
} from '../../../service/admin/access';

/** 后台会员列表。 */
export function useMembersQuery() {
  return useQuery<PageResponse<MemberSummary>>({
    queryKey: ['admin-members'],
    queryFn: () => listMembers(),
  });
}

/** 后台会员详情。 */
export function useMemberQuery(userId: number | null) {
  return useQuery<MemberDetail>({
    queryKey: ['admin-member', userId],
    queryFn: () => getMember(userId as number),
    enabled: userId !== null,
  });
}

/** 后台会员标签和等级更新。 */
export function useMemberMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-members'] });
  };
  return {
    updateTags: useMutation({
      mutationFn: ({ userId, tags }: { userId: number; tags: string[] }) =>
        updateMemberTags(userId, tags),
      retry: 0,
      onSuccess: refresh,
    }),
    updateLevel: useMutation({
      mutationFn: ({ userId, memberLevel }: { userId: number; memberLevel: 'NORMAL' | 'MEMBER' }) =>
        updateMemberLevel(userId, memberLevel),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}
