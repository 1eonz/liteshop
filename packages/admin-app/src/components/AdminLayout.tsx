import type { JSX } from 'react';
import { Link, NavLink, Outlet } from 'react-router-dom';

/** 后台统一路由布局，页面视图通过 Outlet 注入，导航状态由路由驱动。 */
export function AdminLayout(): JSX.Element {
  return (
    <main className="admin-shell">
      <aside className="admin-nav">
        <div className="brand">LiteShop</div>
        <nav aria-label="后台主导航">
          <NavLink to="/" end>
            数据看板
          </NavLink>
          <NavLink to="/products/edit">商品管理</NavLink>
          <NavLink to="/products">商品列表</NavLink>
          <NavLink to="/categories">分类管理</NavLink>
          <NavLink to="/orders">订单管理</NavLink>
          <NavLink to="/inventory">库存管理</NavLink>
          <NavLink to="/settings">系统设置</NavLink>
          <NavLink to="/members">会员管理</NavLink>
          <NavLink to="/audit">审计与权限</NavLink>
          <NavLink to="/page-builder">页面搭建</NavLink>
        </nav>
        <Link className="admin-login-link" to="/login">
          管理员登录
        </Link>
      </aside>
      <section className="content">
        <Outlet />
      </section>
    </main>
  );
}
