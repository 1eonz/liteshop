import type { ProductSummary, StoreComponentSchema } from '@liteshop/shared-types';

export type ProductSort = 'DEFAULT' | 'PRICE_ASC' | 'PRICE_DESC' | 'SALES_DESC';

function readNumberArray(component: StoreComponentSchema, key: string): number[] {
  const value = component.props[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is number => typeof item === 'number' && Number.isInteger(item));
}

/** 读取首页商品板块的排序配置，未知值回退到接口顺序。 */
export function readProductSort(component: StoreComponentSchema): ProductSort {
  const value = component.props.sort;
  return value === 'PRICE_ASC' || value === 'PRICE_DESC' || value === 'SALES_DESC'
    ? value
    : 'DEFAULT';
}

/**
 * 按 Schema 的商品 ID 和排序配置筛选商品。
 * 商品 ID 顺序优先于接口顺序，便于后台搭建器稳定控制首页陈列。
 */
export function selectSchemaProducts(
  component: StoreComponentSchema,
  products: readonly ProductSummary[],
  count: number,
): ProductSummary[] {
  const configuredIds = readNumberArray(component, 'productIds');
  const productsById = new Map(products.map((product) => [product.id, product]));
  const selected = configuredIds.length
    ? configuredIds.flatMap((id) => {
        const product = productsById.get(id);
        return product ? [product] : [];
      })
    : [...products];
  const sort = readProductSort(component);
  return selected
    .sort((left, right) => {
      if (sort === 'PRICE_ASC') return left.minPrice - right.minPrice;
      if (sort === 'PRICE_DESC') return right.minPrice - left.minPrice;
      if (sort === 'SALES_DESC') return right.salesCount - left.salesCount;
      return 0;
    })
    .slice(0, count);
}

/** 返回 Schema 请求需要的最小商品页大小，避免指定商品被分页截断。 */
export function schemaProductPageSize(component: StoreComponentSchema, count: number): number {
  const configuredIds = readNumberArray(component, 'productIds');
  return Math.max(count, configuredIds.length, 20);
}
