export interface HeroSlide {
  eyebrow: string;
  title: string;
  description: string;
  action: string;
  productId: number;
}

/** 首页视觉配置集中维护，页面只负责渲染和导航。 */
export const heroSlides: HeroSlide[] = [
  {
    eyebrow: '今日精选',
    title: '把喜欢的生活带回家',
    description: '精选日常好物，今天下单更快送达',
    action: '探索好物',
    productId: 1,
  },
  {
    eyebrow: '通勤提案',
    title: '轻装出发，也要有好心情',
    description: '从一只保温杯开始，整理你的日常节奏',
    action: '看看保温杯',
    productId: 1,
  },
  {
    eyebrow: '春日上新',
    title: '给家里添一点柔和光线',
    description: '精选小物限时优惠，慢慢布置喜欢的空间',
    action: '浏览人气好物',
    productId: 3,
  },
];

export const homeCategoryLabels = ['新品', '家居', '服饰', '数码', '美妆', '食品', '运动', '礼物'];
