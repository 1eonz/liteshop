import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ContactFormStatus } from '@liteshop/shared-types';
import {
  listContactSubmissions,
  updateContactSubmissionStatus,
} from '../../../service/admin/contact';

/** 官网联系表单查询与状态更新。 */
export function useContactSubmissionsQuery(status?: ContactFormStatus) {
  return useQuery({
    queryKey: ['admin-contact-submissions', status ?? 'all'],
    queryFn: () => listContactSubmissions(status),
  });
}

/** 联系表单状态 mutation，失败不重试，避免重复写入。 */
export function useContactSubmissionMutations() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ submissionId, status }: { submissionId: number; status: ContactFormStatus }) =>
      updateContactSubmissionStatus(submissionId, status),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-contact-submissions'] });
    },
  });
}
