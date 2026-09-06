import axios from 'axios';
import { getAccessToken } from '../store/session';

/** 后台统一 HTTP 客户端，认证、请求 ID 和错误转换在此处集中接入。 */
export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_ADMIN_API_BASE ?? '/api/v1',
  timeout: 10_000,
});

/** 后台只对网络不可用或服务端错误使用演示快照，权限错误不能被掩盖。 */
export function isRecoverableApiError(error: unknown): boolean {
  if (!import.meta.env.DEV) return false;
  if (axios.isAxiosError(error)) return !error.response || error.response.status >= 500;
  return error instanceof Error && error.message === 'API 响应格式无效';
}

httpClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
  if (accessToken) config.headers.set('Authorization', `Bearer ${accessToken}`);
  config.headers.set('X-Request-Id', crypto.randomUUID());
  return config;
});

httpClient.interceptors.response.use((response) => {
  const payload: unknown = response.data;
  if (
    typeof payload === 'string' ||
    !payload ||
    typeof payload !== 'object' ||
    !('data' in payload)
  ) {
    return Promise.reject(new Error('API 响应格式无效'));
  }
  return response;
});
