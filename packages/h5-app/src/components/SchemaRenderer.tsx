import type { FormEvent, JSX } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import type {
  CategorySummary,
  StoreComponentSchema,
  StorePageSchema,
} from '@liteshop/shared-types';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { BottomTabBar } from './BottomTabBar';
import { ProductCard } from './ProductCard';
import { useCategoriesQuery, useProductsQuery } from '../features/catalog';

interface SchemaRendererProps {
  schema: StorePageSchema;
}

interface ComponentViewProps {
  component: StoreComponentSchema;
}

function textProp(component: StoreComponentSchema, key: string, fallback = ''): string {
  const value = component.props[key];
  return typeof value === 'string' ? value : fallback;
}

function numberProp(component: StoreComponentSchema, key: string, fallback: number): number {
  const value = component.props[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function urlProp(component: StoreComponentSchema, key: string): string {
  const value = textProp(component, key);
  if (!value) return '';
  if (value.startsWith('/')) return value;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.toString() : '';
  } catch {
    return '';
  }
}

function SearchBarView({ component }: ComponentViewProps): JSX.Element {
  const navigate = useNavigate();
  const [value, setValue] = useState('');
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const query = value.trim();
    navigate(query ? `/categories?q=${encodeURIComponent(query)}` : '/categories');
  };
  return (
    <form className="schema-search" role="search" onSubmit={submit}>
      <label>
        <span className="sr-only">搜索商品</span>
        <input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={textProp(component, 'placeholder', '搜索商品')}
        />
      </label>
      <button type="submit" aria-label="提交搜索">
        搜索
      </button>
    </form>
  );
}

function BannerView({ component }: ComponentViewProps): JSX.Element {
  const imageUrl = urlProp(component, 'imageUrl');
  const title = textProp(
    component,
    'title',
    component.type === 'Carousel' ? '精选活动' : '活动专区',
  );
  const description = textProp(component, 'description');
  return (
    <section
      className="schema-banner"
      style={imageUrl ? { backgroundImage: `url(${imageUrl})` } : undefined}
    >
      <div>
        <p className="eyebrow">LITESHOP</p>
        <h2>{title}</h2>
        {description && <p>{description}</p>}
      </div>
    </section>
  );
}

function CategoryGridView(): JSX.Element {
  const query = useCategoriesQuery();
  if (query.isLoading) return <FeedbackState>分类加载中…</FeedbackState>;
  if (query.isError) {
    return <ErrorState onRetry={() => void query.refetch()}>分类加载失败，请重试。</ErrorState>;
  }
  const categories = query.data ?? [];
  if (!categories.length)
    return <EmptyState title="暂无分类" description="请先在后台创建商品分类。" />;
  return (
    <section className="section schema-category-grid" aria-labelledby="schema-category-title">
      <div className="section-title">
        <h2 id="schema-category-title">热门分类</h2>
        <Link className="text-action" to="/categories">
          查看全部
        </Link>
      </div>
      <div className="categories">
        {categories.slice(0, 8).map((category: CategorySummary) => (
          <Link className="category" to={`/categories?categoryId=${category.id}`} key={category.id}>
            <span className="category-icon" aria-hidden="true">
              ✦
            </span>
            <span>{category.name}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function ProductDataView({ component }: ComponentViewProps): JSX.Element {
  const count = Math.max(1, Math.min(24, Math.floor(numberProp(component, 'count', 6))));
  const query = useProductsQuery({ pageSize: count });
  if (query.isLoading) return <FeedbackState>商品加载中…</FeedbackState>;
  if (query.isError) {
    return <ErrorState onRetry={() => void query.refetch()}>商品加载失败，请重试。</ErrorState>;
  }
  const products = query.data?.items.slice(0, count) ?? [];
  if (!products.length)
    return <EmptyState title="暂无商品" description="请先发布商品，首页会自动展示。" />;
  const isCarousel = component.type === 'ProductCarousel';
  return (
    <section
      className={isCarousel ? 'section schema-product-carousel' : 'section'}
      aria-labelledby={`schema-product-${component.id}`}
    >
      <div className="section-title">
        <div>
          <p className="eyebrow">商品列表</p>
          <h2 id={`schema-product-${component.id}`}>{textProp(component, 'title', '精选商品')}</h2>
        </div>
        <Link className="text-action" to="/categories">
          查看全部
        </Link>
      </div>
      <div className={isCarousel ? 'schema-product-carousel__track' : 'product-grid'}>
        {products.map((product, index) => (
          <Link
            className={isCarousel ? 'schema-product-carousel__item' : 'product'}
            to={`/product/${product.id}`}
            key={product.id}
          >
            <ProductCard product={{ ...product, imageIndex: index + 1 }} />
          </Link>
        ))}
      </div>
    </section>
  );
}

function CouponView({ component }: ComponentViewProps): JSX.Element {
  return (
    <section className="schema-coupon" aria-label="优惠券">
      <div>
        <strong>{textProp(component, 'title', '领券中心')}</strong>
        <span>{textProp(component, 'description', '满 99 减 10')}</span>
      </div>
      <button type="button">领取</button>
    </section>
  );
}

function ComponentView({ component }: ComponentViewProps): JSX.Element {
  switch (component.type) {
    case 'SearchBar':
      return <SearchBarView component={component} />;
    case 'Carousel':
    case 'ActivityBanner':
    case 'ImageBanner':
      return <BannerView component={component} />;
    case 'CategoryGrid':
      return <CategoryGridView />;
    case 'ProductGrid':
    case 'ProductList':
    case 'ProductCarousel':
      return <ProductDataView component={component} />;
    case 'CouponBlock':
      return <CouponView component={component} />;
    case 'AnnouncementBar':
      return (
        <aside className="schema-announcement" role="status">
          <strong>公告</strong>
          <span>{textProp(component, 'text', '新品已上架，欢迎选购')}</span>
        </aside>
      );
    case 'Tabbar':
      return <BottomTabBar />;
    case 'RichText':
      return <p className="section schema-text">{textProp(component, 'text')}</p>;
    case 'Spacer':
      return <div aria-hidden="true" className="schema-spacer" />;
    default:
      return (
        <EmptyState title="组件暂不可用" description="此组件版本暂不支持，其他内容仍可继续浏览。" />
      );
  }
}

/** 根据版本化 Schema 通过注册表渲染安全组件，未知组件独立降级。 */
export function SchemaRenderer({ schema }: SchemaRendererProps): JSX.Element {
  return (
    <div className="schema-renderer" style={schema.pageStyle}>
      {schema.components.map((component) => (
        <section key={component.id} style={component.style}>
          <ComponentView component={component} />
        </section>
      ))}
    </div>
  );
}
