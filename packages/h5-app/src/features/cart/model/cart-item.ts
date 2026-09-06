import type { CartItem } from '@liteshop/shared-types';

export interface LocalCartLine {
  skuId: number;
  quantity: number;
  priceCents: number;
}

/** 把未登录用户的本地购物车行转换成统一展示模型。 */
export function toLocalCartItem(line: LocalCartLine): CartItem {
  return {
    id: line.skuId,
    skuId: line.skuId,
    skuCode: `DEMO-${line.skuId}`,
    name: `商品 ${line.skuId}`,
    priceCents: line.priceCents,
    quantity: line.quantity,
    specs: {},
    stale: false,
  };
}
