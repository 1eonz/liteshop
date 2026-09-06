import { useMemo } from 'react';
import { demoProducts } from '../features/catalog/model/demo-products';
import type { DemoProduct } from '../features/catalog/model/demo-products';

export { demoProducts } from '../features/catalog/model/demo-products';
export type { DemoProduct } from '../features/catalog/model/demo-products';

/** 首页演示数据选择器，接入真实 API 时由 React Query 替换数据源。 */
export function useCatalogSearch(query: string): DemoProduct[] {
  return useMemo(
    () => demoProducts.filter((product) => product.name.includes(query.trim())),
    [query],
  );
}
