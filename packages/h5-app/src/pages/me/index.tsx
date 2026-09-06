import type { JSX } from 'react';
import { useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BottomTabBar } from '../../components/BottomTabBar';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { logout } from '../../service/auth';
import { getProfile } from '../../service/user';
import { useSessionStore } from '../../store/session';

/** 用户中心页面，集中展示账号、订单、地址和收藏入口。 */
export function MePage(): JSX.Element {
  const navigate = useNavigate();
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const clearSession = useSessionStore((state) => state.clear);
  const profileQuery = useQuery({
    queryKey: ['profile'],
    enabled: authenticated,
    queryFn: getProfile,
  });
  const signOut = useCallback(async () => {
    try {
      await logout();
    } catch {
      /* access token 清理仍需完成 */
    }
    clearSession();
    navigate('/login', { replace: true });
  }, [clearSession, navigate]);
  const [runSignOut, signingOut] = useDebounceAction(signOut, 500);
  if (!authenticated)
    return (
      <main className="trade-page">
        <section className="empty-state">
          <div className="empty-illustration" aria-hidden="true">
            ♡
          </div>
          <h1>登录后管理你的订单</h1>
          <p className="muted">购物车、地址和订单会在登录后同步。</p>
          <Link className="primary-action inline-action" to="/login">
            去登录
          </Link>
        </section>
        <BottomTabBar active="me" />
      </main>
    );
  const profile = profileQuery.data;
  return (
    <main className="trade-page">
      <header className="profile-header">
        <div className="avatar" aria-hidden="true">
          L
        </div>
        <div>
          <p className="eyebrow">LiteShop 会员</p>
          <h1>{profile?.nickname || profile?.phone || '我的账户'}</h1>
          <p className="muted">{profile?.phone ?? '资料加载中…'}</p>
        </div>
      </header>
      <section className="me-links">
        <Link to="/orders">
          <span>我的订单</span>
          <span aria-hidden="true">›</span>
        </Link>
        <Link to="/addresses">
          <span>收货地址</span>
          <span aria-hidden="true">›</span>
        </Link>
        <Link to="/favorites">
          <span>我的收藏</span>
          <span aria-hidden="true">›</span>
        </Link>
      </section>
      {profileQuery.isError && (
        <p className="feedback error-state" role="alert">
          用户资料加载失败，请刷新重试。
        </p>
      )}
      <button
        className="secondary-action wide-action"
        type="button"
        disabled={signingOut}
        onClick={() => void runSignOut()}
      >
        {signingOut ? '退出中…' : '退出登录'}
      </button>
      <BottomTabBar active="me" />
    </main>
  );
}
