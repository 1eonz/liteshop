import type { JSX } from 'react';
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom';
import { useSessionStore } from '../store/session';

/** 后台统一路由布局，页面视图通过 Outlet 注入，导航状态由路由驱动。 */
export function AdminLayout(): JSX.Element {
  const location = useLocation();
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  if (!authenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return (
    <main className="admin-shell">
      <aside className="admin-nav">
        <div className="brand"><span className="brand-mark">L</span><span>LiteShop</span></div>
        <p className="admin-nav__caption">运营工作台</p>
        <nav aria-label="后台主导航">
          <NavLink to="/" end>
            <span className="nav-icon">⌂</span>数据看板
          </NavLink>
          <NavLink to="/products"><span className="nav-icon">▦</span>商品中心</NavLink>
          <NavLink to="/orders"><span className="nav-icon">▤</span>订单管理</NavLink>
          <NavLink to="/inventory"><span className="nav-icon">▥</span>库存管理</NavLink>
          <NavLink to="/members"><span className="nav-icon">♙</span>会员管理</NavLink>
          <NavLink to="/settings"><span className="nav-icon">⚙</span>系统设置</NavLink>
          <div className="admin-nav__section">更多工具</div>
          <NavLink to="/after-sales">售后审核</NavLink>
          <NavLink to="/reviews">评价审核</NavLink>
          <NavLink to="/freight-templates">运费模板</NavLink>
          <NavLink to="/audit">审计与权限</NavLink>
          <NavLink to="/page-builder">页面搭建</NavLink>
          <NavLink to="/contact">联系表单</NavLink>
        </nav>
        <Link className="admin-user" to="/login">
          <span className="admin-user__avatar">林</span><span><b>林晓</b><small>超级管理员</small></span><span aria-hidden="true">⌄</span>
        </Link>
      </aside>
      <section className="content">
        <div className="topbar"><span className="topbar__crumb">LiteShop / 运营工作台</span><div className="topbar__actions"><button className="icon-button" type="button" aria-label="通知">通知</button><span className="topbar__date">2026年09月14日</span></div></div>
        <Outlet />
      </section>
    </main>
  );
}
