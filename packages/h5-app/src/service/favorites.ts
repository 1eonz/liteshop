const favoriteStorageKey = 'liteshop.favorite-products';
import type { ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from './http';

function readIds(): number[] {
  try {
    const raw = window.localStorage.getItem(favoriteStorageKey);
    const values: unknown = raw ? JSON.parse(raw) : [];
    return Array.isArray(values)
      ? values.filter((value): value is number => typeof value === 'number')
      : [];
  } catch {
    return [];
  }
}

/** 读取本地收藏商品 ID，登录后可替换为服务端收藏接口。 */
export function listFavoriteProductIds(): number[] {
  return readIds();
}

/** 切换商品收藏状态。 */
export function toggleFavoriteProduct(productId: number): boolean {
  const ids = readIds();
  const next = ids.includes(productId) ? ids.filter((id) => id !== productId) : [...ids, productId];
  window.localStorage.setItem(favoriteStorageKey, JSON.stringify(next));
  return next.includes(productId);
}

/** 读取服务端收藏，数据库模式下作为唯一事实源。 */
export async function listServerFavoriteProductIds(): Promise<number[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: number[] }>>('/favorites');
  return response.data.data.items;
}

/** 切换服务端收藏状态。 */
export async function toggleServerFavoriteProduct(productId: number): Promise<boolean> {
  const requestId = crypto.randomUUID();
  const response = await httpClient.put<ApiEnvelope<{ productId: number; favorited: boolean }>>(
    `/favorites/${productId}`,
    undefined,
    { headers: { 'X-Request-Id': requestId } },
  );
  return response.data.data.favorited;
}
