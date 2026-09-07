import { create } from 'zustand';

const ACCESS_TOKEN_KEY = 'liteshop.accessToken';
const ACCESS_TOKEN_EXPIRES_AT_KEY = 'liteshop.accessTokenExpiresAt';

function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

function readAccessTokenExpiresAt(): number | null {
  if (typeof window === 'undefined') return null;
  const value = Number(window.localStorage.getItem(ACCESS_TOKEN_EXPIRES_AT_KEY));
  return Number.isFinite(value) && value > 0 ? value : null;
}

interface SessionState {
  accessToken: string | null;
  accessTokenExpiresAt: number | null;
  setAccessToken: (accessToken: string, expiresInSeconds?: number) => void;
  clear: () => void;
}

/** H5 会话状态，统一管理令牌持久化和页面间的认证状态同步。 */
export const useSessionStore = create<SessionState>((set) => ({
  accessToken: readAccessToken(),
  accessTokenExpiresAt: readAccessTokenExpiresAt(),
  setAccessToken: (accessToken, expiresInSeconds) => {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    const accessTokenExpiresAt =
      expiresInSeconds && expiresInSeconds > 0 ? Date.now() + expiresInSeconds * 1000 : null;
    if (accessTokenExpiresAt) {
      window.localStorage.setItem(ACCESS_TOKEN_EXPIRES_AT_KEY, String(accessTokenExpiresAt));
    } else {
      window.localStorage.removeItem(ACCESS_TOKEN_EXPIRES_AT_KEY);
    }
    set({ accessToken, accessTokenExpiresAt });
  },
  clear: () => {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(ACCESS_TOKEN_EXPIRES_AT_KEY);
    set({ accessToken: null, accessTokenExpiresAt: null });
  },
}));

/** 非 React 场景（例如 Axios 拦截器）读取当前访问令牌。 */
export function getAccessToken(): string | null {
  return useSessionStore.getState().accessToken;
}
