import { create } from 'zustand';

const ADMIN_ACCESS_TOKEN_KEY = 'liteshop.admin.accessToken';

function readAccessToken(): string | null {
  if (typeof window === 'undefined') return null;
  return window.localStorage.getItem(ADMIN_ACCESS_TOKEN_KEY);
}

interface SessionState {
  accessToken: string | null;
  setAccessToken: (accessToken: string) => void;
  clear: () => void;
}

/** 后台会话客户端状态，不缓存服务端业务数据。 */
export const useSessionStore = create<SessionState>((set) => ({
  accessToken: readAccessToken(),
  setAccessToken: (accessToken) => {
    window.localStorage.setItem(ADMIN_ACCESS_TOKEN_KEY, accessToken);
    set({ accessToken });
  },
  clear: () => {
    window.localStorage.removeItem(ADMIN_ACCESS_TOKEN_KEY);
    set({ accessToken: null });
  },
}));

/** 非 React 场景（例如 Axios 拦截器）读取当前后台访问令牌。 */
export function getAccessToken(): string | null {
  return useSessionStore.getState().accessToken;
}
