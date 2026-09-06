import { ProductStatus, type ProductSummary } from '@liteshop/shared-types';

export type DemoProduct = Pick<
  ProductSummary,
  'id' | 'name' | 'minPrice' | 'maxPrice' | 'coverUrl' | 'salesCount' | 'status'
> & { imageIndex: number };

/** 开发环境 API 不可用时使用的商品快照，属于商品领域而非客户端状态。 */
export const demoProducts: DemoProduct[] = [
  {
    id: 1,
    name: '晨雾保温杯',
    minPrice: 12900,
    maxPrice: 12900,
    coverUrl: '',
    salesCount: 128,
    status: ProductStatus.ON_SHELF,
    imageIndex: 1,
  },
  {
    id: 2,
    name: '云朵卫衣',
    minPrice: 26900,
    maxPrice: 26900,
    coverUrl: '',
    salesCount: 96,
    status: ProductStatus.ON_SHELF,
    imageIndex: 2,
  },
  {
    id: 3,
    name: '柔光台灯',
    minPrice: 18900,
    maxPrice: 18900,
    coverUrl: '',
    salesCount: 74,
    status: ProductStatus.ON_SHELF,
    imageIndex: 3,
  },
  {
    id: 4,
    name: '山野香氛',
    minPrice: 15900,
    maxPrice: 15900,
    coverUrl: '',
    salesCount: 52,
    status: ProductStatus.ON_SHELF,
    imageIndex: 4,
  },
];
