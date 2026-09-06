import { lazy, Suspense, type JSX } from 'react';
import type { RouteObject } from 'react-router-dom';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AdminLayout } from '../components/AdminLayout';
import { RouteFallback } from './RouteFallback';

const DashboardPage = lazy(async () => ({ default: (await import('../pages/dashboard')).DashboardPage }));
const ProductEditorPage = lazy(async () => ({
  default: (await import('../pages/products/editor')).ProductEditorPage,
}));
const ProductsPage = lazy(async () => ({ default: (await import('../pages/products')).ProductsPage }));
const CategoriesPage = lazy(async () => ({ default: (await import('../pages/categories')).CategoriesPage }));
const OrdersPage = lazy(async () => ({ default: (await import('../pages/orders')).OrdersPage }));
const InventoryPage = lazy(async () => ({ default: (await import('../pages/inventory')).InventoryPage }));
const SettingsPage = lazy(async () => ({ default: (await import('../pages/settings')).SettingsPage }));
const AuditPage = lazy(async () => ({ default: (await import('../pages/audit')).AuditPage }));
const AdminLoginPage = lazy(async () => ({ default: (await import('../pages/login')).AdminLoginPage }));
const MembersPage = lazy(async () => ({ default: (await import('../pages/members')).MembersPage }));
const PageBuilderPage = lazy(async () => ({
  default: (await import('../pages/page-builder')).PageBuilderPage,
}));

function withSuspense(element: JSX.Element): JSX.Element {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

/** 后台路由集中配置，页面分片按需加载，权限守卫由 AdminLayout 统一接入。 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AdminLayout />,
    children: [
      { index: true, element: withSuspense(<DashboardPage />) },
      { path: 'products/edit', element: withSuspense(<ProductEditorPage />) },
      { path: 'products/edit/:productId', element: withSuspense(<ProductEditorPage />) },
      { path: 'products', element: withSuspense(<ProductsPage />) },
      { path: 'categories', element: withSuspense(<CategoriesPage />) },
      { path: 'orders', element: withSuspense(<OrdersPage />) },
      { path: 'inventory', element: withSuspense(<InventoryPage />) },
      { path: 'settings', element: withSuspense(<SettingsPage />) },
      { path: 'audit', element: withSuspense(<AuditPage />) },
      { path: 'members', element: withSuspense(<MembersPage />) },
      { path: 'page-builder', element: withSuspense(<PageBuilderPage />) },
    ],
  },
  { path: '/login', element: withSuspense(<AdminLoginPage />) },
  { path: '*', element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
