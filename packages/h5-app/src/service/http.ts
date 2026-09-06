import axios from 'axios';

/** H5 统一 HTTP 客户端，认证、错误转换和请求 ID 在 service 层集中接入。 */
export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api/v1',
  timeout: 10_000,
});

/** 仅把网络不可用或服务端错误视为演示数据回退，权限和业务错误必须继续抛出。 */
export function isRecoverableApiError(error: unknown): boolean {
  if (!import.meta.env.DEV) return false;
  if (axios.isAxiosError(error)) return !error.response || error.response.status >= 500;
  return error instanceof Error && error.message === 'API 响应格式无效';
}

httpClient.interceptors.request.use((config) => {
  const accessToken = window.localStorage.getItem('liteshop.accessToken');
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
