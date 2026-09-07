import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ProductStatus } from '@liteshop/shared-types';
import type {
  ProductCreateInput,
  ProductDetailResponse,
  ProductSummary,
  ProductUpdateInput,
} from '@liteshop/shared-types';
import {
  createAdminProduct,
  getAdminProduct,
  listAdminProducts,
  updateAdminProduct,
} from '../../../service/admin/catalog';
import { isRecoverableApiError } from '../../../service/http';

const demoProducts: ProductSummary[] = [
  {
    id: 1,
    name: '晨雾保温杯',
    coverUrl: '',
    minPrice: 12900,
    maxPrice: 12900,
    salesCount: 128,
    status: ProductStatus.ON_SHELF,
  },
  {
    id: 2,
    name: '云朵卫衣',
    coverUrl: '',
    minPrice: 26900,
    maxPrice: 26900,
    salesCount: 96,
    status: ProductStatus.ON_SHELF,
  },
];

/** 后台商品查询，开发 API 不可用时保留可浏览的本地快照。 */
export function useAdminProductsQuery(query: { q?: string } = {}) {
  return useQuery({
    queryKey: ['admin-products', query],
    queryFn: async () => {
      try {
        return await listAdminProducts(query);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        const items = query.q
          ? demoProducts.filter((product) => product.name.includes(query.q ?? ''))
          : demoProducts;
        return { items, meta: { page: 1, pageSize: 20, total: items.length, hasNext: false } };
      }
    },
  });
}

/** 后台商品详情查询，接口不可用时沿用同一套演示商品快照。 */
export function useAdminProductQuery(productId: number | null) {
  return useQuery<ProductDetailResponse>({
    queryKey: ['admin-product', productId],
    queryFn: async () => {
      if (productId === null) throw new Error('商品 ID 无效');
      try {
        return await getAdminProduct(productId);
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
          seoTitle: null,
          seoDescription: null,
          seoKeywords: null,
          specDefinitions: [
            {
              id: 1,
              name: '容量',
              sortOrder: 0,
              values: [{ id: 1, value: '480ml', sortOrder: 0 }],
            },
          ],
          skus: [
            {
              skuId: product.id,
              skuCode: `DEMO-${product.id}`,
              name: '标准款',
              priceCents: product.minPrice,
              quantity: 100,
              specs: { 容量: '480ml' },
            },
          ],
        };
      }
    },
    enabled: productId !== null,
  });
}

/** 后台商品创建 mutation。 */
export function useCreateAdminProductMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ProductCreateInput) => createAdminProduct(input),
    retry: 0,
    onSuccess: (product) => {
      queryClient.setQueryData(['admin-product', product.id], product);
      void queryClient.invalidateQueries({ queryKey: ['admin-products'] });
    },
  });
}

/** 后台商品更新 mutation。 */
export function useUpdateAdminProductMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ productId, input }: { productId: number; input: ProductUpdateInput }) =>
      updateAdminProduct(productId, input),
    retry: 0,
    onSuccess: (product, variables) => {
      queryClient.setQueryData(['admin-product', variables.productId], product);
      void queryClient.invalidateQueries({ queryKey: ['admin-products'] });
    },
  });
}
