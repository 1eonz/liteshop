import type { ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface AdminLoginInput {
  phone: string;
  code: string;
}

export interface AdminLoginResult {
  accessToken: string;
  refreshToken?: string;
}

/** 管理端登录 API，页面不直接依赖 HTTP 客户端。 */
export async function loginAdmin(input: AdminLoginInput): Promise<AdminLoginResult> {
  const response = await httpClient.post<ApiEnvelope<AdminLoginResult>>('/auth/login', input);
  return response.data.data;
}
