import type { JSX } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSessionStore } from '../store/session';
import { messages } from '../i18n/messages';

const copy = messages.navigation;
const primaryLinks = [
  ['/', copy.dashboard], ['/products', copy.products], ['/categories', copy.categories],
  ['/orders', copy.orders], ['/inventory', copy.inventory], ['/members', copy.members], ['/settings', copy.settings],
] as const;
const toolLinks = [
  ['/after-sales', copy.afterSales], ['/reviews', copy.reviews], ['/freight-templates', copy.freight],
  ['/audit', copy.audit], ['/page-builder', copy.builder], ['/contact', copy.contact],
] as const;

/** 后台统一路由布局，页面视图通过 Outlet 注入，导航状态由路由驱动。 */
export function AdminLayout(): JSX.Element {
  const location = useLocation();
  const queryClient = useQueryClient();
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const clearSession = useSessionStore((state) => state.clear);
  const currentTitle = [...primaryLinks, ...toolLinks].find(([path]) =>
    path === '/' ? location.pathname === '/' : location.pathname.startsWith(path),
  )?.[1] ?? copy.workspace;
  const logout = (): void => {
    clearSession();
    queryClient.clear();
  };
  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return (
    <div className="admin-shell">
      <a className="skip-link" href="#admin-content">{copy.skip}</a>
      <aside className="admin-nav">
        <div className="brand"><span className="brand-mark" aria-hidden="true">L</span><span>LiteShop</span></div>
        <p className="admin-nav__caption">{copy.workspace}</p>
        <nav aria-label={copy.main}>
          {primaryLinks.map(([path, title]) => <NavLink to={path} end={path === '/'} key={path}>{title}</NavLink>)}
          <div className="admin-nav__section">{copy.tools}</div>
          {toolLinks.map(([path, title]) => <NavLink to={path} key={path}>{title}</NavLink>)}
        </nav>
        <div className="admin-user"><span>{copy.account}</span><button className="ghost-button" type="button" onClick={logout}>{copy.logout}</button></div>
      </aside>
      <main className="content" id="admin-content" tabIndex={-1}>
        <div className="topbar"><span className="topbar__crumb">LiteShop / {currentTitle}{location.pathname.startsWith('/products/') ? ` / ${copy.productEditor}` : ''}</span><time className="topbar__date" dateTime={new Date().toISOString().slice(0, 10)}>{new Intl.DateTimeFormat('zh-CN', { dateStyle: 'long' }).format(new Date())}</time></div>
        <Outlet />
      </main>
    </div>
  );
}
