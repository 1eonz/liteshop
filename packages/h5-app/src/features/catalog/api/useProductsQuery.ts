import { useQuery } from '@tanstack/react-query';
import type { ProductDetailResponse } from '@liteshop/shared-types';
import { demoProducts } from '../../../store/catalog';
import { getProduct, listProducts, type ProductListQuery } from '../../../service/products';
import { isRecoverableApiError } from '../../../service/http';

const demoPage = (
  query: ProductListQuery,
): {
  items: typeof demoProducts;
  meta: { page: number; pageSize: number; total: number; hasNext: boolean };
} => {
  const items = query.q
    ? demoProducts.filter((product) => product.name.includes(query.q ?? ''))
    : demoProducts;
  const page = query.page ?? 1;
  const pageSize = query.pageSize ?? 20;
  return {
    items,
    meta: {
      page,
      pageSize,
      total: items.length,
      hasNext: page * pageSize < items.length,
    },
  };
};

/** 商品服务端状态查询，页面只通过 Hook 消费 API 数据。 */
export function useProductsQuery(query: ProductListQuery = {}) {
  return useQuery({
    queryKey: ['products', query],
    queryFn: async () => {
      try {
        return await listProducts(query);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoPage(query);
      }
    },
  });
}

/** 商品详情查询，开发环境 API 未启动时使用同一套演示商品快照。 */
export function useProductQuery(productId: number) {
  return useQuery<ProductDetailResponse>({
    queryKey: ['product', productId],
    queryFn: async () => {
      try {
        return await getProduct(productId);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        const product = demoProducts.find((item) => item.id === productId);
        if (!product) throw error;
        return {
          ...product,
          subtitle: '轻盈材质，适合每日通勤',
          brand: 'LiteShop',
          description: '食品级材质，简洁耐用，支持全天候生活场景。',
          detailHtml: '',
          detailImages: [],
          specDefinitions: [
            {
              id: 1,
              name: '规格',
              sortOrder: 0,
              values: [{ id: 1, value: '标准款', sortOrder: 0 }],
            },
          ],
          skus: [
            {
              skuId: product.id,
              skuCode: `DEMO-${product.id}`,
              name: '标准款',
              priceCents: product.minPrice,
              quantity: 100,
              specs: { 规格: '标准款' },
            },
          ],
        };
      }
    },
  });
}
