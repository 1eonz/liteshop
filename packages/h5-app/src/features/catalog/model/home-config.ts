import type { StorePageSchema } from '@liteshop/shared-types';

/**
 * API 不可用时的开发演示 Schema。
 * 兜底仍然走同一套 SchemaRenderer，避免维护第二套首页 JSX。
 */
export const defaultStoreHomePage: StorePageSchema = {
  id: 1,
  slug: 'home',
  channel: 'store',
  name: '首页',
  title: 'LiteShop',
  status: 'PUBLISHED',
  version: 1,
  isHome: true,
  components: [
    {
      id: 'search-bar-1',
      type: 'SearchBar',
      props: { brand: 'LiteShop', placeholder: '搜索商品', searchPath: '/search' },
      style: {},
    },
    {
      id: 'carousel-1',
      type: 'Carousel',
      props: {
        autoplay: true,
        intervalMs: 5000,
        items: [
          {
            eyebrow: '今日精选',
            title: '把喜欢的生活带回家',
            description: '精选日常好物，今天下单更快送达',
            action: '探索好物',
            href: '/product/1',
          },
          {
            eyebrow: '通勤提案',
            title: '轻装出发，也要有好心情',
            description: '从一只保温杯开始，整理你的日常节奏',
            action: '看看保温杯',
            href: '/product/1',
          },
          {
            eyebrow: '春日上新',
            title: '给家里添一点柔和光线',
            description: '精选小物限时优惠，慢慢布置喜欢的空间',
            action: '浏览人气好物',
            href: '/categories',
          },
        ],
      },
      style: {},
    },
    {
      id: 'category-grid-1',
      type: 'CategoryGrid',
      props: {
        title: '热门分类',
        columns: 4,
        showAll: true,
        allLabel: '查看全部',
        allHref: '/categories',
      },
      style: {},
    },
    {
      id: 'product-grid-1',
      type: 'ProductGrid',
      props: {
        eyebrow: '商品列表',
        title: '人气好物',
        count: 4,
        showAll: true,
        allLabel: '热销榜',
        allHref: '/categories',
      },
      style: {},
    },
    {
      id: 'activity-banner-1',
      type: 'ActivityBanner',
      props: {
        eyebrow: '限时活动',
        title: '春日好物',
        description: '低至 7 折',
        actionLabel: '去看看',
        href: '/categories',
      },
      style: {},
    },
    {
      id: 'tabbar-1',
      type: 'Tabbar',
      props: { items: ['home', 'category', 'cart', 'me'] },
      style: {},
    },
  ],
};
