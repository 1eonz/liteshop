import { describe, expect, it } from 'vitest';
import { products } from './app-data';
import { toLocalCartItem } from './features/cart';

describe('H5 首页数据', () => {
  it('包含四个精选商品', () => {
    expect(products).toHaveLength(4);
  });

  it('将本地购物车行转换为统一商品模型', () => {
    expect(toLocalCartItem({ skuId: 7, quantity: 2, priceCents: 1999 })).toMatchObject({
      id: 7,
      skuId: 7,
      quantity: 2,
      priceCents: 1999,
    });
  });
});
