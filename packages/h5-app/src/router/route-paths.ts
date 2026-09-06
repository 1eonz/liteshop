/** H5 对外路径清单，避免测试和导航散落硬编码路径。 */
export const H5_ROUTE_PATHS = {
  home: '/',
  product: '/product/:productId',
  cart: '/cart',
  orderConfirm: '/order/confirm',
  login: '/login',
  me: '/me',
  orders: '/orders',
  orderDetail: '/orders/:orderId',
  payment: '/payment/:orderId',
  addresses: '/addresses',
  favorites: '/favorites',
  categories: '/categories',
  notifications: '/notifications',
} as const;
