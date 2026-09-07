export type SiteComponentType =
  | 'Navbar'
  | 'Footer'
  | 'Section'
  | 'Divider'
  | 'Hero'
  | 'HeroSplit'
  | 'Hero3D'
  | 'Features'
  | 'Stats'
  | 'LogoWall'
  | 'Testimonials'
  | 'Pricing'
  | 'FAQ'
  | 'ImageWithText'
  | 'ContactForm'
  | 'CTA'
  | 'Hero3DBackground'
  | 'Product3DViewer';

export interface SiteAnimationConfig {
  enabled: boolean;
  type: 'fade-up' | 'fade-down' | 'fade-left' | 'fade-right' | 'zoom-in' | 'none';
}

export interface SiteComponentSchema {
  id: string;
  type: SiteComponentType;
  props: Record<string, unknown>;
  style?: Record<string, string>;
  animation?: SiteAnimationConfig;
}

export interface SiteSeo {
  title: string;
  description: string;
  keywords: string[];
  noIndex?: boolean;
}

export interface SitePageSchema {
  slug: string;
  title: string;
  description: string;
  pageStyle?: Record<string, string>;
  seo: SiteSeo;
  components: SiteComponentSchema[];
}

export const siteTitle = 'LiteShop';

const image = (id: string): string =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=1200&q=80`;

const commonFooter: SiteComponentSchema = {
  id: 'footer',
  type: 'Footer',
  props: {
    groups: [
      {
        title: '产品',
        links: [
          { label: '商城搭建', href: '/products' },
          { label: '数据看板', href: '/products#analytics' },
        ],
      },
      {
        title: '支持',
        links: [
          { label: '帮助中心', href: '/about#faq' },
          { label: '联系团队', href: '/contact' },
        ],
      },
      {
        title: '关于',
        links: [
          { label: '品牌故事', href: '/about' },
          { label: '服务条款', href: '/about#terms' },
        ],
      },
    ],
    copyright: '© 2026 LiteShop. 用更轻的方式经营每一笔订单。',
  },
};

const homePage: SitePageSchema = {
  slug: 'home',
  title: '让每一笔交易都更轻盈',
  description: 'LiteShop 为成长中的品牌提供一套清晰、可靠、可持续扩展的商城工作台。',
  seo: {
    title: 'LiteShop | 轻盈经营每一笔订单',
    description: '从商品、库存到订单和数据看板，LiteShop 让团队专注于真正重要的增长。',
    keywords: ['LiteShop', '商城系统', '订单管理', '库存管理'],
  },
  components: [
    {
      id: 'navbar',
      type: 'Navbar',
      props: {
        links: [
          { label: '产品能力', href: '/products' },
          { label: '品牌故事', href: '/about' },
          { label: '联系团队', href: '/contact' },
        ],
        cta: { label: '开始体验', href: '/contact' },
      },
    },
    {
      id: 'hero',
      type: 'HeroSplit',
      props: {
        eyebrow: 'LITESHOP COMMERCE OS',
        title: '让每一笔交易都更轻盈',
        description: '商品、库存、订单与内容，在一个安静而有力量的工作台里自然协同。',
        primaryAction: { label: '预约演示', href: '/contact' },
        secondaryAction: { label: '查看能力', href: '/products' },
        image: image('photo-1556742049-0cfed4f6a45d'),
        imageAlt: '团队在明亮工作台前协作',
      },
      animation: { enabled: true, type: 'fade-up' },
    },
    {
      id: 'features',
      type: 'Features',
      props: {
        eyebrow: '一套系统，覆盖关键动作',
        title: '把复杂留给系统，把时间还给团队',
        items: [
          {
            icon: '01',
            title: '交易清晰',
            description: '从购物车到支付回调，每个状态都有明确边界。',
          },
          {
            icon: '02',
            title: '库存可靠',
            description: '三层库存模型与原子扣减，避免超卖与错账。',
          },
          { icon: '03', title: '决策及时', description: '实时看板聚合销售、库存和履约信号。' },
        ],
      },
      animation: { enabled: true, type: 'fade-up' },
    },
    {
      id: 'stats',
      type: 'Stats',
      props: {
        items: [
          { value: '99.95%', label: '订单链路可用性' },
          { value: '3 层', label: '库存安全模型' },
          { value: '24/7', label: '业务状态可追踪' },
        ],
      },
    },
    {
      id: 'image-text',
      type: 'ImageWithText',
      props: {
        eyebrow: '为真实团队而设计',
        title: '让运营动作变得可预期',
        description: '清晰的权限、可回溯的操作日志和可复用的页面组件，帮助团队稳定地把事情做对。',
        image: image('photo-1556761175-b413da4baf72'),
        imageAlt: '团队在会议室讨论数据',
        action: { label: '了解架构', href: '/about#architecture' },
      },
    },
    {
      id: 'logos',
      type: 'LogoWall',
      props: {
        title: '被认真经营的品牌正在使用 LiteShop',
        items: ['NORTH', 'MORI', 'KINDRED', 'FIELD', 'STUDIO'],
      },
    },
    {
      id: 'testimonials',
      type: 'Testimonials',
      props: {
        items: [
          {
            quote: '我们终于可以用同一套语言讨论商品、库存和订单。',
            name: '林岚',
            role: '运营负责人 · Mori Home',
          },
          {
            quote: '看板让每天的补货决策从经验变成了事实。',
            name: '周野',
            role: '供应链负责人 · North Field',
          },
        ],
      },
    },
    {
      id: 'pricing',
      type: 'Pricing',
      props: {
        eyebrow: '简单透明的开始',
        title: '从今天开始，把系统搭起来',
        plans: [
          {
            name: 'Starter',
            price: '¥0',
            period: '/月',
            description: '适合验证产品与流程',
            features: ['商品与 SKU 管理', '基础订单工作台', '标准数据看板'],
            action: { label: '免费开始', href: '/contact' },
          },
          {
            name: 'Growth',
            price: '¥699',
            period: '/月',
            description: '适合正在增长的团队',
            features: ['包含 Starter 全部能力', '高级库存与履约', '多角色权限与审计'],
            recommended: true,
            action: { label: '预约演示', href: '/contact' },
          },
          {
            name: 'Scale',
            price: '定制',
            period: '',
            description: '适合多品牌与复杂业务',
            features: ['包含 Growth 全部能力', '多租户与数据隔离', '专属架构支持'],
            action: { label: '联系团队', href: '/contact' },
          },
        ],
      },
    },
    {
      id: 'faq',
      type: 'FAQ',
      props: {
        title: '常见问题',
        items: [
          {
            question: '可以接入现有商品和订单数据吗？',
            answer: '可以。通过版本化 API 和导入工具接入现有数据，迁移过程保留原有标识。',
          },
          {
            question: '团队可以按角色分配权限吗？',
            answer: '可以。管理员、运营、财务和仓管可以拥有不同的菜单与操作权限。',
          },
          {
            question: '是否支持自定义品牌风格？',
            answer: '支持。商城与官网共用 Design Tokens，可配置主色、导航和组件样式。',
          },
        ],
      },
    },
    {
      id: 'cta',
      type: 'CTA',
      props: {
        title: '准备好让经营变轻了吗？',
        description: '留下联系方式，我们会带你走一遍真实业务流程。',
        action: { label: '预约一次对话', href: '/contact' },
      },
    },
    commonFooter,
  ],
};

const aboutPage: SitePageSchema = {
  slug: 'about',
  title: '为长期经营而做的系统',
  description: 'LiteShop 从交易的真实摩擦出发，构建可解释、可扩展的商城基础设施。',
  seo: {
    title: '关于 LiteShop',
    description: '了解 LiteShop 的产品理念与工程方法。',
    keywords: ['LiteShop', '品牌故事'],
  },
  components: [
    {
      id: 'navbar',
      type: 'Navbar',
      props: {
        links: [
          { label: '产品能力', href: '/products' },
          { label: '品牌故事', href: '/about' },
          { label: '联系团队', href: '/contact' },
        ],
        cta: { label: '开始体验', href: '/contact' },
      },
    },
    {
      id: 'hero',
      type: 'Hero',
      props: {
        eyebrow: 'OUR APPROACH',
        title: '系统应该让人更从容，而不是更忙碌',
        description: '我们把复杂的业务规则写进系统，把清晰的判断留给每一个使用它的人。',
        action: { label: '看看产品能力', href: '/products' },
        image: image('photo-1497366811353-6870744d04b2'),
        imageAlt: '安静明亮的工作空间',
      },
    },
    {
      id: 'architecture',
      type: 'Section',
      props: {
        id: 'architecture',
        eyebrow: 'ENGINEERING PRINCIPLES',
        title: '四个坚持',
        body: '契约先行、边界清晰、状态可追踪、失败可恢复。',
      },
    },
    {
      id: 'values',
      type: 'Features',
      props: {
        items: [
          { icon: 'A', title: '可解释', description: '每个金额、状态和库存变化都有来源。' },
          { icon: 'B', title: '可复用', description: '共享类型、组件和令牌，减少重复实现。' },
          { icon: 'C', title: '可恢复', description: '幂等、回滚和错误态让系统面对意外。' },
          { icon: 'D', title: '可成长', description: '从单店到多品牌，架构边界保持稳定。' },
        ],
      },
    },
    {
      id: 'faq',
      type: 'FAQ',
      props: {
        title: '常见问题',
        items: [
          {
            question: 'LiteShop 适合什么团队？',
            answer: '适合正在从人工表格和多套工具迁移到统一工作台的电商团队。',
          },
          {
            question: '可以自托管吗？',
            answer: '可以。项目采用 Docker Compose 与清晰的环境隔离规范，支持自托管部署。',
          },
        ],
      },
    },
    commonFooter,
  ],
};

const productsPage: SitePageSchema = {
  slug: 'products',
  title: '从商品到复购，能力自然衔接',
  description: '一套围绕真实经营动作组织的模块化能力。',
  seo: {
    title: 'LiteShop 产品能力',
    description: '商品、库存、订单、数据看板和低代码页面能力。',
    keywords: ['商品管理', '库存管理', '订单系统'],
  },
  components: [
    {
      id: 'navbar',
      type: 'Navbar',
      props: {
        links: [
          { label: '产品能力', href: '/products' },
          { label: '品牌故事', href: '/about' },
          { label: '联系团队', href: '/contact' },
        ],
        cta: { label: '开始体验', href: '/contact' },
      },
    },
    {
      id: 'hero',
      type: 'Hero',
      props: {
        eyebrow: 'PRODUCT SYSTEM',
        title: '把每一个经营动作，放回它该在的位置',
        description: '模块化能力按业务边界组织，团队可以从最需要的地方开始。',
        action: { label: '预约演示', href: '/contact' },
        image: image('photo-1556740749-887f6717d7e4'),
        imageAlt: '手持手机查看商城数据',
      },
    },
    {
      id: 'capabilities',
      type: 'Features',
      props: {
        title: '核心能力',
        items: [
          { icon: '01', title: '商品与 SKU', description: 'SPU、规格、价格和上下架状态统一管理。' },
          {
            icon: '02',
            title: '三层库存',
            description: '可用、锁定、实际库存清晰分离，支持原子扣减。',
          },
          {
            icon: '03',
            title: '订单与支付',
            description: '状态机、幂等键和回调验签守护资金链路。',
          },
          { icon: '04', title: '低代码页面', description: '用版本化 Schema 组合商城和官网页面。' },
        ],
      },
    },
    {
      id: 'analytics',
      type: 'ImageWithText',
      props: {
        id: 'analytics',
        eyebrow: 'DECISION LAYER',
        title: '看板只呈现真正需要的信号',
        description: '销售趋势、商品排行、库存预警和履约状态在一个视图里汇聚。',
        image: image('photo-1551288049-bebda4e38f71'),
        imageAlt: '数据分析图表',
      },
    },
    {
      id: 'cta',
      type: 'CTA',
      props: {
        title: '从一个真实流程开始',
        description: '我们会根据你的商品和订单结构，给出清晰的落地路径。',
        action: { label: '联系团队', href: '/contact' },
      },
    },
    commonFooter,
  ],
};

const contactPage: SitePageSchema = {
  slug: 'contact',
  title: '聊聊你的下一步',
  description: '告诉我们你正在解决什么问题，我们会在一个工作日内回复。',
  seo: {
    title: '联系 LiteShop',
    description: '联系 LiteShop 团队，预约产品演示。',
    keywords: ['联系 LiteShop', '预约演示'],
  },
  components: [
    {
      id: 'navbar',
      type: 'Navbar',
      props: {
        links: [
          { label: '产品能力', href: '/products' },
          { label: '品牌故事', href: '/about' },
          { label: '联系团队', href: '/contact' },
        ],
      },
    },
    {
      id: 'hero',
      type: 'Hero',
      props: {
        eyebrow: "LET'S TALK",
        title: '把你的真实问题带来',
        description: '不需要准备一份完美的需求文档，从当前最费力的环节开始就好。',
      },
    },
    {
      id: 'form',
      type: 'ContactForm',
      props: { title: '预约一次对话', description: '填写下面的信息，我们会通过邮件或电话联系你。' },
    },
    commonFooter,
  ],
};

export const sitePages: Record<string, SitePageSchema> = {
  home: homePage,
  about: aboutPage,
  products: productsPage,
  contact: contactPage,
};

export const getSitePage = (slug: string): SitePageSchema | null => sitePages[slug] ?? null;
