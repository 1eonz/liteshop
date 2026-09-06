import type { ApiEnvelope, LoginRequest, SmsCodeRequest } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 发送登录短信验证码。 */
export async function sendSmsCode(input: SmsCodeRequest): Promise<{ sent: boolean }> {
  const response = await httpClient.post<ApiEnvelope<{ sent: boolean }>>('/auth/sms-code', input);
  return response.data.data;
}

/** 使用手机号和验证码登录。 */
export async function login(
  input: LoginRequest,
): Promise<{ accessToken: string; expiresIn: number; subject: string }> {
  const response = await httpClient.post<
    ApiEnvelope<{ accessToken: string; expiresIn: number; subject: string }>
  >('/auth/login', input);
  return response.data.data;
}

/** 清理服务端刷新 Cookie。 */
export async function logout(): Promise<void> {
  await httpClient.post<ApiEnvelope<{ loggedOut: boolean }>>('/auth/logout');
}
