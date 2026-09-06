import { useQuery } from '@tanstack/react-query';
import { listProducts, type ProductListQuery } from '../service/products';

/** 后台商品服务端状态查询，统一由 React Query 管理缓存。 */
export function useProductsQuery(query: ProductListQuery = {}) {
  return useQuery({
    queryKey: ['admin-products', query],
    queryFn: () => listProducts(query),
  });
}
