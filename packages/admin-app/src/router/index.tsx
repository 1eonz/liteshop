import type { RouteObject } from 'react-router-dom';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AdminLayout } from '../components/AdminLayout';
import { DashboardPage } from '../pages/dashboard';
import { ProductEditorPage } from '../pages/products/editor';
import { OrdersPage } from '../pages/orders';
import { InventoryPage } from '../pages/inventory';
import { SettingsPage } from '../pages/settings';
import { ProductsPage } from '../pages/products';
import { CategoriesPage } from '../pages/categories';
import { AuditPage } from '../pages/audit';
import { AdminLoginPage } from '../pages/login';
import { MembersPage } from '../pages/members';
import { PageBuilderPage } from '../pages/page-builder';

/** 后台路由集中配置，权限守卫可在此处统一接入。 */
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AdminLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'products/edit', element: <ProductEditorPage /> },
      { path: 'products/edit/:productId', element: <ProductEditorPage /> },
      { path: 'products', element: <ProductsPage /> },
      { path: 'categories', element: <CategoriesPage /> },
      { path: 'orders', element: <OrdersPage /> },
      { path: 'inventory', element: <InventoryPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: 'audit', element: <AuditPage /> },
      { path: 'members', element: <MembersPage /> },
      { path: 'page-builder', element: <PageBuilderPage /> },
    ],
  },
  { path: '/login', element: <AdminLoginPage /> },
  { path: '*', element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
