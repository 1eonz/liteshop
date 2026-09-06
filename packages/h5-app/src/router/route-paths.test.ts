import { describe, expect, it } from 'vitest';
import { H5_ROUTE_PATHS } from './route-paths';

describe('H5 路由路径', () => {
  it('保留商品、交易和账户公开路径', () => {
    expect(Object.values(H5_ROUTE_PATHS)).toEqual(
      expect.arrayContaining(['/','/product/:productId','/cart','/order/confirm','/login','/me']),
    );
  });

  it('动态路由使用命名参数而非读取 window.location', () => {
    expect(H5_ROUTE_PATHS.product).toBe('/product/:productId');
    expect(H5_ROUTE_PATHS.orderDetail).toBe('/orders/:orderId');
    expect(H5_ROUTE_PATHS.payment).toBe('/payment/:orderId');
  });
});
