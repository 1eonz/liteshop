import type { ComponentType, FormEvent, JSX } from 'react';
import { lazy, Suspense, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type { StoreComponentSchema, StorePageSchema } from '@liteshop/shared-types';
import { EmptyState, FeedbackState } from '@liteshop/shared-components';
import { BottomTabBar, type TabBarItem } from './BottomTabBar';
import { useDebounceAction } from '../hooks/useDebounceAction';
import {
  booleanProp,
  isInternalPath,
  numberProp,
  pathProp,
  safeSchemaUrl,
  textProp,
  urlProp,
} from './schema/schema-props';

const LazyCategoryGridView = lazy(async () => {
  const module = await import('./schema/CategoryGridView');
  return { default: module.CategoryGridView };
});
const LazyProductDataView = lazy(async () => {
  const module = await import('./schema/ProductDataView');
  return { default: module.ProductDataView };
});

interface SchemaRendererProps {
  schema: StorePageSchema;
}

interface ComponentViewProps {
  component: StoreComponentSchema;
}

function SearchBarView({ component }: ComponentViewProps): JSX.Element {
  const navigate = useNavigate();
  const [value, setValue] = useState('');
  const brand = textProp(component, 'brand');
  const searchPath = pathProp(component, 'searchPath', '/categories');
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const query = value.trim();
    navigate(query ? `${searchPath}?q=${encodeURIComponent(query)}` : searchPath);
  };
  return (
    <header className="h5-header">
      {brand ? <span className="brand">{brand}</span> : null}
      <form className="search-field schema-search" role="search" onSubmit={submit}>
        <label>
          <span className="sr-only">搜索商品</span>
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder={textProp(component, 'placeholder', '搜索商品')}
          />
        </label>
        <button type="submit" aria-label="提交搜索">
          {textProp(component, 'submitLabel', '搜索')}
        </button>
      </form>
    </header>
  );
}

interface CarouselItem {
  eyebrow: string;
  title: string;
  description: string;
  action: string;
  href: string;
  imageUrl: string;
}

function carouselHref(value: unknown): string {
  return safeSchemaUrl(value);
}

function readCarouselItems(component: StoreComponentSchema): CarouselItem[] {
  const value = component.props.items;
  if (!Array.isArray(value)) return [];
  return value.flatMap((item): CarouselItem[] => {
    if (!item || typeof item !== 'object') return [];
    const record = item as Record<string, unknown>;
    const title = typeof record.title === 'string' ? record.title : '';
    if (!title) return [];
    return [
      {
        eyebrow: typeof record.eyebrow === 'string' ? record.eyebrow : '',
        title,
        description: typeof record.description === 'string' ? record.description : '',
        action: typeof record.action === 'string' ? record.action : '',
        href: carouselHref(record.href),
        imageUrl: safeSchemaUrl(record.imageUrl),
      },
    ];
  });
}

function CarouselView({ component }: ComponentViewProps): JSX.Element {
  const items = readCarouselItems(component);
  const [activeIndex, setActiveIndex] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const autoplay = booleanProp(component, 'autoplay', true);
  const intervalMs = Math.max(3000, Math.min(15000, numberProp(component, 'intervalMs', 5000)));

  useEffect(() => {
    if (isPaused || !autoplay || items.length < 2) return undefined;
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return undefined;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    const timer = window.setInterval(() => {
      setActiveIndex((current) => (current + 1) % items.length);
    }, intervalMs);
    return () => window.clearInterval(timer);
  }, [autoplay, intervalMs, isPaused, items.length]);

  useEffect(() => {
    setActiveIndex((current) => Math.min(current, Math.max(items.length - 1, 0)));
  }, [items.length]);

  if (!items.length) return <BannerView component={component} />;
  const activeItem = items[Math.min(activeIndex, items.length - 1)];
  const move = (offset: number): void => {
    setActiveIndex((current) => (current + offset + items.length) % items.length);
  };
  return (
    <section
      className="hero"
      role="region"
      aria-roledescription="carousel"
      aria-label={textProp(component, 'ariaLabel', '精选活动轮播')}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={(event) => {
        const nextTarget = event.relatedTarget;
        if (!(nextTarget instanceof Node) || !event.currentTarget.contains(nextTarget)) {
          setIsPaused(false);
        }
      }}
      style={activeItem.imageUrl ? { backgroundImage: `url(${activeItem.imageUrl})` } : undefined}
    >
      <div className="hero-copy" aria-live={isPaused ? 'polite' : 'off'}>
        {activeItem.eyebrow ? <p className="eyebrow">{activeItem.eyebrow}</p> : null}
        <h1 id={`hero-title-${component.id}`}>{activeItem.title}</h1>
        {activeItem.description ? <p>{activeItem.description}</p> : null}
        {activeItem.action && activeItem.href ? (
          activeItem.href.startsWith('/') ? (
            <Link className="hero-action" to={activeItem.href}>
              {activeItem.action}
            </Link>
          ) : (
            <a
              className="hero-action"
              href={activeItem.href}
              rel="noopener noreferrer"
              target="_blank"
            >
              {activeItem.action}
            </a>
          )
        ) : null}
      </div>
      {items.length > 1 ? (
        <div className="hero-controls">
          <button
            className="hero-control"
            type="button"
            onClick={() => move(-1)}
            aria-label="上一张轮播图"
          >
            ‹
          </button>
          <div className="hero-dots" role="tablist" aria-label="选择轮播图">
            {items.map((item, index) => (
              <button
                className={index === activeIndex ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={index === activeIndex}
                aria-label={`查看第 ${index + 1} 张轮播图`}
                key={`${item.title}-${index}`}
                onClick={() => setActiveIndex(index)}
              />
            ))}
          </div>
          <button
            className="hero-control"
            type="button"
            onClick={() => move(1)}
            aria-label="下一张轮播图"
          >
            ›
          </button>
        </div>
      ) : null}
    </section>
  );
}

function BannerView({ component }: ComponentViewProps): JSX.Element {
  const imageUrl = urlProp(component, 'imageUrl');
  const title = textProp(
    component,
    'title',
    component.type === 'ActivityBanner' ? '活动专区' : '精选活动',
  );
  const description = textProp(component, 'description');
  const isActivity = component.type === 'ActivityBanner';
  return (
    <section
      className={isActivity ? 'section activity' : 'hero'}
      style={imageUrl ? { backgroundImage: `url(${imageUrl})` } : undefined}
    >
      <div>
        <p className="eyebrow">{textProp(component, 'eyebrow', 'LITESHOP')}</p>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
      {isActivity && textProp(component, 'actionLabel') && pathProp(component, 'href', '') ? (
        <Link className="text-action" to={pathProp(component, 'href', '')}>
          {textProp(component, 'actionLabel')}
        </Link>
      ) : null}
    </section>
  );
}

function CouponView({ component }: ComponentViewProps): JSX.Element {
  const [claimed, setClaimed] = useState(false);
  const [claim, claiming] = useDebounceAction(async () => {
    setClaimed(true);
  }, 300);
  const actionLabel = textProp(component, 'actionLabel', '领取');
  return (
    <section className="schema-coupon" aria-label="优惠券">
      <div>
        <strong>{textProp(component, 'title', '领券中心')}</strong>
        <span>{textProp(component, 'description', '满 99 减 10')}</span>
      </div>
      <button type="button" disabled={claiming || claimed} onClick={() => void claim()}>
        {claimed ? textProp(component, 'claimedLabel', '已领取') : actionLabel}
      </button>
    </section>
  );
}

const DEFAULT_TAB_ITEMS: Record<TabBarItem['key'], TabBarItem> = {
  home: { key: 'home', label: '首页', to: '/' },
  category: { key: 'category', label: '分类', to: '/categories' },
  cart: { key: 'cart', label: '购物车', to: '/cart' },
  me: { key: 'me', label: '我的', to: '/me' },
};

function readTabItems(component: StoreComponentSchema): TabBarItem[] {
  const value = component.props.items;
  if (!Array.isArray(value)) return Object.values(DEFAULT_TAB_ITEMS);
  return value.flatMap((item): TabBarItem[] => {
    const key =
      typeof item === 'string' && item in DEFAULT_TAB_ITEMS
        ? (item as TabBarItem['key'])
        : item && typeof item === 'object' && 'key' in item && typeof item.key === 'string'
          ? (item.key as TabBarItem['key'])
          : null;
    if (!key || !DEFAULT_TAB_ITEMS[key]) return [];
    const record =
      typeof item === 'object' && item !== null ? (item as Record<string, unknown>) : {};
    const label = typeof record.label === 'string' ? record.label : DEFAULT_TAB_ITEMS[key].label;
    const to =
      typeof record.to === 'string' && isInternalPath(record.to)
        ? record.to
        : DEFAULT_TAB_ITEMS[key].to;
    return [{ key, label, to }];
  });
}

function AnnouncementView({ component }: ComponentViewProps): JSX.Element {
  return (
    <aside className="schema-announcement" role="status">
      <strong>{textProp(component, 'label', '公告')}</strong>
      <span>{textProp(component, 'text', '新品已上架，欢迎选购')}</span>
    </aside>
  );
}

function TabbarView({ component }: ComponentViewProps): JSX.Element {
  return <BottomTabBar items={readTabItems(component)} />;
}

function RichTextView({ component }: ComponentViewProps): JSX.Element {
  return <p className="section schema-text">{textProp(component, 'text')}</p>;
}

function SpacerView(): JSX.Element {
  return <div aria-hidden="true" className="schema-spacer" />;
}

function UnsupportedView(): JSX.Element {
  return (
    <EmptyState title="组件暂不可用" description="此组件版本暂不支持，其他内容仍可继续浏览。" />
  );
}

type ComponentRenderer = ComponentType<ComponentViewProps>;

function LazySchemaSection({ component }: ComponentViewProps): JSX.Element {
  return (
    <Suspense fallback={<FeedbackState>内容加载中…</FeedbackState>}>
      {component.type === 'CategoryGrid' ? (
        <LazyCategoryGridView component={component} />
      ) : (
        <LazyProductDataView component={component} />
      )}
    </Suspense>
  );
}

const COMPONENT_RENDERERS: Partial<Record<StoreComponentSchema['type'], ComponentRenderer>> = {
  SearchBar: SearchBarView,
  Carousel: CarouselView,
  ActivityBanner: BannerView,
  ImageBanner: BannerView,
  CategoryGrid: LazySchemaSection,
  ProductGrid: LazySchemaSection,
  ProductList: LazySchemaSection,
  ProductCarousel: LazySchemaSection,
  CouponBlock: CouponView,
  AnnouncementBar: AnnouncementView,
  Tabbar: TabbarView,
  RichText: RichTextView,
  Spacer: SpacerView,
};

function ComponentView({ component }: ComponentViewProps): JSX.Element {
  const Renderer = COMPONENT_RENDERERS[component.type] ?? UnsupportedView;
  return <Renderer component={component} />;
}

/** 根据版本化 Schema 通过注册表渲染安全组件，未知组件独立降级。 */
export function SchemaRenderer({ schema }: SchemaRendererProps): JSX.Element {
  return (
    <div className="schema-renderer" style={schema.pageStyle}>
      {schema.components.map((component, index) => (
        <div
          className="schema-component"
          data-component-id={component.id || `${component.type}-${index}`}
          key={component.id || `${component.type}-${index}`}
          style={component.style}
        >
          <ComponentView component={component} />
        </div>
      ))}
    </div>
  );
}
