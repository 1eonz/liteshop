import { lazy, Suspense, type JSX } from 'react';
import type { RouteObject } from 'react-router-dom';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RouteFallback } from './RouteFallback';
import { H5_ROUTE_PATHS } from './route-paths';

const HomePage = lazy(async () => ({ default: (await import('../pages/home')).HomePage }));
const ProductDetailPage = lazy(async () => ({
  default: (await import('../pages/product-detail')).ProductDetailPage,
}));
const CartPage = lazy(async () => ({ default: (await import('../pages/cart')).CartPage }));
const OrderConfirmPage = lazy(async () => ({
  default: (await import('../pages/order-confirm')).OrderConfirmPage,
}));
const LoginPage = lazy(async () => ({ default: (await import('../pages/login')).LoginPage }));
const MePage = lazy(async () => ({ default: (await import('../pages/me')).MePage }));
const OrdersPage = lazy(async () => ({ default: (await import('../pages/orders')).OrdersPage }));
const OrderDetailPage = lazy(async () => ({
  default: (await import('../pages/order-detail')).OrderDetailPage,
}));
const PaymentPage = lazy(async () => ({
  default: (await import('../pages/payment')).PaymentPage,
}));
const AddressesPage = lazy(async () => ({
  default: (await import('../pages/addresses')).AddressesPage,
}));
const FavoritesPage = lazy(async () => ({
  default: (await import('../pages/favorites')).FavoritesPage,
}));
const CategoriesPage = lazy(async () => ({
  default: (await import('../pages/categories')).CategoriesPage,
}));
const NotificationsPage = lazy(async () => ({
  default: (await import('../pages/notifications')).NotificationsPage,
}));
const PreviewPage = lazy(async () => ({
  default: (await import('../pages/preview')).PreviewPage,
}));

function withSuspense(element: JSX.Element): JSX.Element {
  return <Suspense fallback={<RouteFallback />}>{element}</Suspense>;
}

/** 所有 H5 页面路由集中维护，页面组件不读取 window.location。 */
export const routes: RouteObject[] = [
  { path: H5_ROUTE_PATHS.home, element: withSuspense(<HomePage />) },
  { path: H5_ROUTE_PATHS.product, element: withSuspense(<ProductDetailPage />) },
  { path: H5_ROUTE_PATHS.cart, element: withSuspense(<CartPage />) },
  { path: H5_ROUTE_PATHS.orderConfirm, element: withSuspense(<OrderConfirmPage />) },
  { path: H5_ROUTE_PATHS.login, element: withSuspense(<LoginPage />) },
  { path: H5_ROUTE_PATHS.me, element: withSuspense(<MePage />) },
  { path: H5_ROUTE_PATHS.orders, element: withSuspense(<OrdersPage />) },
  { path: H5_ROUTE_PATHS.orderDetail, element: withSuspense(<OrderDetailPage />) },
  { path: H5_ROUTE_PATHS.payment, element: withSuspense(<PaymentPage />) },
  { path: H5_ROUTE_PATHS.addresses, element: withSuspense(<AddressesPage />) },
  { path: H5_ROUTE_PATHS.favorites, element: withSuspense(<FavoritesPage />) },
  { path: H5_ROUTE_PATHS.categories, element: withSuspense(<CategoriesPage />) },
  { path: H5_ROUTE_PATHS.notifications, element: withSuspense(<NotificationsPage />) },
  { path: H5_ROUTE_PATHS.preview, element: withSuspense(<PreviewPage />) },
  { path: '*', element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
