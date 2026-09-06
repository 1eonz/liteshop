import { useQuery } from '@tanstack/react-query';
import type { CartResponse } from '@liteshop/shared-types';
import { getCart } from '../../../service/cart';
import { isRecoverableApiError } from '../../../service/http';

const EMPTY_CART: CartResponse = { items: [] };

/** 购物车服务端状态查询，页面仅消费统一 Hook。 */
export function useCartQuery(enabled: boolean) {
  return useQuery({
    queryKey: ['cart', enabled],
    enabled,
    queryFn: async (): Promise<CartResponse> => {
      try {
        return await getCart();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return EMPTY_CART;
      }
    },
  });
}
