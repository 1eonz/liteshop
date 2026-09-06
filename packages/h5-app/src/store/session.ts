import { create } from 'zustand';

const ACCESS_TOKEN_KEY = 'liteshop.accessToken';

function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

interface SessionState {
  accessToken: string | null;
  setAccessToken: (accessToken: string) => void;
  clear: () => void;
}

/** H5 会话状态，统一管理令牌持久化和页面间的认证状态同步。 */
export const useSessionStore = create<SessionState>((set) => ({
  accessToken: readAccessToken(),
  setAccessToken: (accessToken) => {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    set({ accessToken });
  },
  clear: () => {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    set({ accessToken: null });
  },
}));

/** 非 React 场景（例如 Axios 拦截器）读取当前访问令牌。 */
export function getAccessToken(): string | null {
  return useSessionStore.getState().accessToken;
}
