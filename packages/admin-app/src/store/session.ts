import { create } from 'zustand';

interface SessionState {
  accessToken: string | null;
  setAccessToken: (accessToken: string) => void;
  clear: () => void;
}

/** 后台会话客户端状态，不缓存服务端业务数据。 */
export const useSessionStore = create<SessionState>((set) => ({
  accessToken: null,
  setAccessToken: (accessToken) => set({ accessToken }),
  clear: () => set({ accessToken: null }),
}));
