import type { ApiEnvelope, ContactFormStatus, ContactSubmission } from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 读取官网联系表单，可按处理状态筛选。 */
export async function listContactSubmissions(
  status?: ContactFormStatus,
): Promise<ContactSubmission[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: ContactSubmission[] }>>(
    '/admin/contact/forms',
    { params: status ? { status } : undefined },
  );
  return response.data.data.items;
}

/** 更新联系表单处理状态。 */
export async function updateContactSubmissionStatus(
  submissionId: number,
  status: ContactFormStatus,
): Promise<ContactSubmission> {
  const response = await httpClient.put<ApiEnvelope<ContactSubmission>>(
    `/admin/contact/forms/${submissionId}`,
    { status },
  );
  return response.data.data;
}
