import { useQuery } from '@tanstack/react-query';
import type { ProductListQuery } from '@liteshop/shared-types';
import { listProducts } from '../service/products';

/** 后台商品服务端状态查询，统一由 React Query 管理缓存。 */
export function useProductsQuery(query: ProductListQuery = {}) {
  return useQuery({
    queryKey: ['admin-products', query],
    queryFn: () => listProducts(query),
  });
}
