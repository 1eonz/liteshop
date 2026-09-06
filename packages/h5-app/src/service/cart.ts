import type { ApiEnvelope, CartItem, CartResponse } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface CartItemInput {
  skuId: number;
  quantity: number;
  priceCents: number;
}

/** 读取服务端购物车。 */
export async function getCart(): Promise<CartResponse> {
  const response = await httpClient.get<ApiEnvelope<CartResponse>>('/cart');
  return response.data.data;
}

/** 添加购物车项，写操作由调用方负责防抖。 */
export async function addCartItem(input: CartItemInput): Promise<CartItem> {
  const response = await httpClient.post<ApiEnvelope<{ item: CartItem }>>('/cart/items', input);
  return response.data.data.item;
}

export async function updateCartItem(skuId: number, input: CartItemInput): Promise<CartItem> {
  const response = await httpClient.put<ApiEnvelope<{ item: CartItem }>>(
    `/cart/items/${skuId}`,
    input,
  );
  return response.data.data.item;
}

export async function removeCartItem(skuId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ removed: boolean }>>(`/cart/items/${skuId}`);
}
