import type { RouteObject } from 'react-router-dom';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { CartPage } from '../pages/cart';
import { HomePage } from '../pages/home';
import { OrderConfirmPage } from '../pages/order-confirm';
import { ProductDetailPage } from '../pages/product-detail';
import { LoginPage } from '../pages/login';
import { MePage } from '../pages/me';
import { OrdersPage } from '../pages/orders';
import { OrderDetailPage } from '../pages/order-detail';
import { PaymentPage } from '../pages/payment';
import { AddressesPage } from '../pages/addresses';
import { FavoritesPage } from '../pages/favorites';
import { CategoriesPage } from '../pages/categories';
import { NotificationsPage } from '../pages/notifications';

/** 所有 H5 页面路由集中维护，页面组件不读取 window.location。 */
export const routes: RouteObject[] = [
  { path: '/', element: <HomePage /> },
  { path: '/product/:productId', element: <ProductDetailPage /> },
  { path: '/cart', element: <CartPage /> },
  { path: '/order/confirm', element: <OrderConfirmPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/me', element: <MePage /> },
  { path: '/orders', element: <OrdersPage /> },
  { path: '/orders/:orderId', element: <OrderDetailPage /> },
  { path: '/payment/:orderId', element: <PaymentPage /> },
  { path: '/addresses', element: <AddressesPage /> },
  { path: '/favorites', element: <FavoritesPage /> },
  { path: '/categories', element: <CategoriesPage /> },
  { path: '/notifications', element: <NotificationsPage /> },
  { path: '*', element: <Navigate to="/" replace /> },
];

export const router = createBrowserRouter(routes);
