import { describe, expect, it } from 'vitest';
import { ProductStatus, type ProductSummary } from '@liteshop/shared-types';
import { products } from './app-data';
import { toLocalCartItem } from './features/cart';
import { defaultStoreHomePage } from './features/catalog';
import { normalizeStoreHomePage } from './features/catalog/api/useStorePageQuery';
import { schemaProductPageSize, selectSchemaProducts } from './features/catalog/model/schema-products';
import { formatPrice } from '@liteshop/shared-types';

describe('H5 首页数据', () => {
  it('包含四个精选商品', () => {
    expect(products).toHaveLength(4);
  });

  it('将本地购物车行转换为统一商品模型', () => {
    expect(toLocalCartItem({ skuId: 7, quantity: 2, priceCents: 1999 })).toMatchObject({
      id: 7,
      skuId: 7,
      quantity: 2,
      priceCents: 1999,
    });
  });

  it('统一使用整数分金额格式化', () => {
    expect(formatPrice(1999)).toBe('¥19.99');
    expect(formatPrice(Number.NaN)).toBe('-');
  });

  it('首页开发回退仍使用与线上相同的 Schema 板块', () => {
    expect(defaultStoreHomePage.components.map((component) => component.type)).toEqual([
      'SearchBar',
      'Carousel',
      'CategoryGrid',
      'ProductGrid',
      'ActivityBanner',
      'Tabbar',
    ]);
    expect(defaultStoreHomePage.components.every((component) => component.id.length > 0)).toBe(
      true,
    );
  });

  it('默认轮播启用自动播放且配置可被后台覆盖', () => {
    const carousel = defaultStoreHomePage.components.find(
      (component) => component.type === 'Carousel',
    );
    expect(carousel?.props.autoplay).toBe(true);
    expect(carousel?.props.intervalMs).toBe(5000);
    expect(carousel?.props.items).toHaveLength(3);
  });

  it('不会因后台组件使用空样式而替换整个首页 Schema', () => {
    const schema = {
      ...defaultStoreHomePage,
      title: '后台定制首页',
      components: [
        {
          ...defaultStoreHomePage.components[0],
          id: 'custom-search',
          style: {},
        },
      ],
    };
    expect(normalizeStoreHomePage(schema)).toMatchObject({
      title: '后台定制首页',
      components: [{ id: 'custom-search', style: {} }],
    });
  });

  it('为缺少组件 ID 的后台 Schema 生成稳定 ID', () => {
    const schema = {
      ...defaultStoreHomePage,
      components: [{ ...defaultStoreHomePage.components[0], id: '' }],
    };
    expect(normalizeStoreHomePage(schema).components[0].id).toBe('searchbar-1');
  });

  it('归一化时过滤非法组件并清理非字符串样式值', () => {
    const schema = {
      ...defaultStoreHomePage,
      components: [
        {
          type: 'RichText',
          props: { text: '可用' },
          style: { color: 'var(--color-text-primary)', gap: 8 },
        },
        null,
        { type: '', props: {}, style: {} },
      ],
    } as unknown as typeof defaultStoreHomePage;
    expect(normalizeStoreHomePage(schema).components).toEqual([
      {
        id: 'richtext-1',
        type: 'RichText',
        props: { text: '可用' },
        style: { color: 'var(--color-text-primary)' },
      },
    ]);
  });

  it('为重复的后台组件 ID 生成稳定后缀', () => {
    const schema = {
      ...defaultStoreHomePage,
      components: [
        { ...defaultStoreHomePage.components[0], id: 'duplicate' },
        { ...defaultStoreHomePage.components[1], id: 'duplicate' },
      ],
    };
    expect(normalizeStoreHomePage(schema).components.map((component) => component.id)).toEqual([
      'duplicate',
      'duplicate-2',
    ]);
  });

  it('归一化页面样式时只保留字符串值', () => {
    const schema = {
      ...defaultStoreHomePage,
      pageStyle: { background: 'var(--color-bg-page)', '--invalid': 12 },
    } as unknown as typeof defaultStoreHomePage;
    expect(normalizeStoreHomePage(schema).pageStyle).toEqual({
      background: 'var(--color-bg-page)',
    });
  });

  it('按首页 Schema 指定顺序和排序消费商品', () => {
    const component = {
      id: 'products',
      type: 'ProductGrid',
      props: { productIds: [3, 1], sort: 'PRICE_DESC' },
      style: {},
    } as const;
    const products: ProductSummary[] = [
      { id: 1, name: '一', coverUrl: '', minPrice: 100, maxPrice: 100, salesCount: 20, status: ProductStatus.ON_SHELF },
      { id: 3, name: '三', coverUrl: '', minPrice: 300, maxPrice: 300, salesCount: 5, status: ProductStatus.ON_SHELF },
      { id: 8, name: '八', coverUrl: '', minPrice: 800, maxPrice: 800, salesCount: 80, status: ProductStatus.ON_SHELF },
    ];
    expect(selectSchemaProducts(component, products, 2).map((product) => product.id)).toEqual([3, 1]);
    expect(schemaProductPageSize(component, 2)).toBe(20);
  });
});
