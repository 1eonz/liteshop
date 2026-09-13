import type {
  StoreComponentSchema,
  StoreComponentType,
  StorePageSchema,
} from '@liteshop/shared-types';

export const PAGE_BUILDER_STORAGE_KEY = 'liteshop.page-builder.draft';
export const PAGE_BUILDER_MAX_HISTORY = 50;

export interface ComponentGroup {
  label: string;
  types: StoreComponentType[];
}

export interface PageTemplate {
  key: string;
  label: string;
  components: StoreComponentSchema[];
}

export const COMPONENT_GROUPS: ComponentGroup[] = [
  { label: '基础内容', types: ['SearchBar', 'Carousel', 'ImageBanner', 'Spacer', 'RichText'] },
  {
    label: '商品运营',
    types: ['CategoryGrid', 'ProductGrid', 'ProductList', 'ProductCarousel', 'CouponBlock'],
  },
  { label: '转化组件', types: ['ActivityBanner', 'AnnouncementBar', 'Tabbar'] },
];

export const SITE_COMPONENT_GROUPS: ComponentGroup[] = [
  { label: '官网结构', types: ['Navbar', 'Footer', 'Section', 'Divider'] },
  {
    label: '官网内容',
    types: ['Hero', 'HeroSplit', 'Features', 'Stats', 'LogoWall', 'Testimonials'],
  },
  { label: '官网转化', types: ['Pricing', 'FAQ', 'ImageWithText', 'ContactForm', 'CTA'] },
];

export const DEFAULT_PAGE: StorePageSchema = {
  id: 1,
  slug: 'home',
  name: '首页',
  title: '商城首页',
  channel: 'store',
  version: 1,
  isHome: true,
  components: [
    { id: 'search-1', type: 'SearchBar', props: { placeholder: '搜索商品' }, style: {} },
    { id: 'carousel-1', type: 'Carousel', props: { title: '精选活动' }, style: {} },
    { id: 'category-1', type: 'CategoryGrid', props: { columns: 4 }, style: {} },
    { id: 'product-1', type: 'ProductGrid', props: { columns: 2 }, style: {} },
    { id: 'banner-1', type: 'ActivityBanner', props: { title: '限时活动' }, style: {} },
    {
      id: 'tabbar-1',
      type: 'Tabbar',
      props: { items: ['home', 'category', 'cart', 'me'] },
      style: {},
    },
  ],
};

export const DEFAULT_SITE_PAGE: StorePageSchema = {
  ...DEFAULT_PAGE,
  slug: 'site-home',
  name: '官网首页',
  title: '官网首页',
  channel: 'site',
  isHome: false,
  components: [
    { id: 'site-navbar-1', type: 'Navbar', props: { title: 'LiteShop 官网' }, style: {} },
    { id: 'site-hero-1', type: 'HeroSplit', props: { title: '让每一笔交易都更轻盈' }, style: {} },
    { id: 'site-features-1', type: 'Features', props: { title: '核心能力' }, style: {} },
    { id: 'site-contact-1', type: 'ContactForm', props: { title: '预约一次对话' }, style: {} },
    { id: 'site-footer-1', type: 'Footer', props: { title: 'LiteShop' }, style: {} },
  ],
};

export const PAGE_TEMPLATES: PageTemplate[] = [
  { key: 'minimal', label: '简洁上新', components: DEFAULT_PAGE.components.slice(0, 4) },
  {
    key: 'campaign',
    label: '活动转化',
    components: [
      {
        id: 'announcement-template',
        type: 'AnnouncementBar',
        props: { text: '今日下单享包邮' },
        style: {},
      },
      {
        id: 'coupon-template',
        type: 'CouponBlock',
        props: { title: '新人券', description: '满 99 减 10' },
        style: {},
      },
      {
        id: 'product-carousel-template',
        type: 'ProductCarousel',
        props: { title: '热销推荐' },
        style: {},
      },
    ],
  },
  {
    key: 'content',
    label: '内容导购',
    components: [
      { id: 'image-template', type: 'ImageBanner', props: { title: '品牌故事' }, style: {} },
      {
        id: 'rich-text-template',
        type: 'RichText',
        props: { text: '用一段文字介绍你的品牌与服务。' },
        style: {},
      },
      { id: 'category-template', type: 'CategoryGrid', props: { columns: 4 }, style: {} },
    ],
  },
];

/** 从浏览器草稿恢复 Schema，异常内容回退为稳定的默认商城页面。 */
export function readPageDraft(): StorePageSchema {
  if (typeof window === 'undefined') return DEFAULT_PAGE;
  try {
    const raw = window.localStorage.getItem(PAGE_BUILDER_STORAGE_KEY);
    if (!raw) return DEFAULT_PAGE;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return DEFAULT_PAGE;
    const draft = parsed as Partial<StorePageSchema>;
    if (!Array.isArray(draft.components)) return DEFAULT_PAGE;
    return { ...DEFAULT_PAGE, ...draft, components: draft.components as StoreComponentSchema[] };
  } catch {
    return DEFAULT_PAGE;
  }
}

/** 返回组件库统一中文名称。 */
export function componentLabel(type: StoreComponentType): string {
  const labels: Record<StoreComponentType, string> = {
    SearchBar: '搜索框',
    Carousel: '轮播图',
    CategoryGrid: '分类导航',
    ProductGrid: '商品网格',
    ActivityBanner: '图片广告',
    Tabbar: '底部导航',
    RichText: '富文本',
    ImageBanner: '图片横幅',
    Spacer: '辅助空白',
    ProductList: '商品列表',
    ProductCarousel: '商品横滑',
    CouponBlock: '优惠券',
    AnnouncementBar: '公告栏',
    Navbar: '官网导航',
    Footer: '官网页脚',
    Section: '官网区块',
    Divider: '官网分隔线',
    Hero: '官网主视觉',
    HeroSplit: '官网图文主视觉',
    Hero3D: '官网 3D 主视觉',
    Features: '官网能力列表',
    Stats: '官网数据指标',
    LogoWall: '官网品牌墙',
    Testimonials: '官网客户评价',
    Pricing: '官网价格方案',
    FAQ: '官网常见问题',
    ImageWithText: '官网图文区块',
    ContactForm: '官网联系表单',
    CTA: '官网行动召唤',
    Hero3DBackground: '官网 3D 背景',
    Product3DViewer: '官网产品预览',
  };
  return labels[type];
}

/** 生成画布项目的可读摘要。 */
export function previewCopy(component: StoreComponentSchema): string {
  const props = component.props;
  if (typeof props.title === 'string') return props.title;
  if (typeof props.text === 'string') return props.text;
  if (typeof props.placeholder === 'string') return props.placeholder;
  return componentLabel(component.type);
}

/** 打开 H5 草稿预览窗口，并返回是否被浏览器允许。 */
export function openPagePreview(page: StorePageSchema): boolean {
  const previewBase = import.meta.env.VITE_H5_PREVIEW_URL ?? 'http://127.0.0.1:5173';
  const previewUrl = new URL('/preview', previewBase);
  previewUrl.searchParams.set('schema', JSON.stringify(page));
  return window.open(previewUrl.toString(), '_blank', 'noopener,noreferrer') !== null;
}
