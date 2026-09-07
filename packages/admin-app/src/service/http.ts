import axios from 'axios';
import type { ApiEnvelope } from '@liteshop/shared-types';
import { getAccessToken } from '../store/session';
import { useSessionStore } from '../store/session';

/** 后台统一 HTTP 客户端，认证、请求 ID 和错误转换在此处集中接入。 */
export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_ADMIN_API_BASE ?? '/api/v1',
  timeout: 10_000,
  withCredentials: true,
});

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_ADMIN_API_BASE ?? '/api/v1',
  timeout: 10_000,
  withCredentials: true,
});

let refreshPromise: Promise<string | null> | null = null;

interface RefreshTokenPayload {
  accessToken: string;
  expiresIn?: number;
}

function readRefreshTokenPayload(payload: unknown): RefreshTokenPayload {
  if (!payload || typeof payload !== 'object' || !('data' in payload)) {
    throw new Error('刷新令牌响应格式无效');
  }
  const data = payload.data;
  if (!data || typeof data !== 'object' || !('accessToken' in data)) {
    throw new Error('刷新令牌响应格式无效');
  }
  const accessToken = data.accessToken;
  if (typeof accessToken !== 'string' || accessToken.length === 0) {
    throw new Error('刷新令牌响应格式无效');
  }
  const expiresIn =
    'expiresIn' in data && typeof data.expiresIn === 'number' ? data.expiresIn : undefined;
  return { accessToken, expiresIn };
}

async function refreshAccessToken(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<ApiEnvelope<{ accessToken: string }>>('/auth/refresh')
      .then((response) => {
        const token = readRefreshTokenPayload(response.data);
        useSessionStore.getState().setAccessToken(token.accessToken, token.expiresIn);
        return token.accessToken;
      })
      .catch(() => {
        useSessionStore.getState().clear();
        return null;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/** 后台只对网络不可用或服务端错误使用演示快照，权限错误不能被掩盖。 */
export function isRecoverableApiError(error: unknown): boolean {
  if (!import.meta.env.DEV) return false;
  if (axios.isAxiosError(error)) return !error.response || error.response.status >= 500;
  return error instanceof Error && error.message === 'API 响应格式无效';
}

httpClient.interceptors.request.use((config) => {
  const accessToken = getAccessToken();
  if (accessToken) config.headers.set('Authorization', `Bearer ${accessToken}`);
  if (!config.headers.get('X-Request-Id')) config.headers.set('X-Request-Id', crypto.randomUUID());
  return config;
});

httpClient.interceptors.response.use(
  (response) => {
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
  },
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || error.response?.status !== 401 || !error.config) {
      return Promise.reject(error);
    }
    const requestConfig = error.config as typeof error.config & { _liteshopRetried?: boolean };
    const requestUrl = requestConfig.url ?? '';
    if (
      requestConfig._liteshopRetried ||
      requestUrl.includes('/auth/login') ||
      requestUrl.includes('/auth/refresh') ||
      requestUrl.includes('/auth/logout')
    ) {
      return Promise.reject(error);
    }
    const accessToken = await refreshAccessToken();
    if (!accessToken) return Promise.reject(error);
    requestConfig._liteshopRetried = true;
    requestConfig.headers.set('Authorization', `Bearer ${accessToken}`);
    return httpClient.request(requestConfig);
  },
);
