import { afterEach, describe, expect, it } from 'vitest';
import { useCartStore } from './cart';

describe('购物车本地状态', () => {
  afterEach(() => {
    useCartStore.getState().clear();
  });

  it('删除失败时可以通过 upsert 恢复已移除商品', () => {
    const line = { skuId: 7, quantity: 2, priceCents: 1999 };
    useCartStore.getState().addLine(line);
    useCartStore.getState().removeLine(line.skuId);

    useCartStore.getState().upsertLine(line);

    expect(useCartStore.getState().lines).toEqual([line]);
  });
});
