import type { JSX } from 'react';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ProductCard } from '../../components/ProductCard';
import { BottomTabBar } from '../../components/BottomTabBar';
import { useProductsQuery } from '../../features/catalog/api/useProductsQuery';
import { heroSlides, homeCategoryLabels, useStoreHomePageQuery } from '../../features/catalog';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { SchemaRenderer } from '../../components/SchemaRenderer';

/** H5 首页视图，页面只编排组件，不直接发起 API 请求。 */
export function HomePage(): JSX.Element {
  const [query, setQuery] = useState('');
  const navigate = useNavigate();
  const [activeSlide, setActiveSlide] = useState(0);
  const storePageQuery = useStoreHomePageQuery();
  const productsQuery = useProductsQuery({ q: query || undefined });
  const visibleProducts = productsQuery.data?.items ?? [];
  const hero = heroSlides[activeSlide];
  const moveSlide = (offset: number): void => {
    setActiveSlide((current) => (current + offset + heroSlides.length) % heroSlides.length);
  };
  if (storePageQuery.isLoading) {
    return (
      <main className="h5-shell">
        <FeedbackState>首页加载中…</FeedbackState>
      </main>
    );
  }
  if (storePageQuery.data?.components.length) {
    return (
      <main className="h5-shell">
        <SchemaRenderer schema={storePageQuery.data} />
      </main>
    );
  }
  return (
    <main className="h5-shell">
      <header className="h5-header">
        <span className="brand">LiteShop</span>
        <form
          className="search-field"
          role="search"
          onSubmit={(event) => {
            event.preventDefault();
            const next = query.trim();
            if (next) navigate(`/search?q=${encodeURIComponent(next)}`);
          }}
        >
          <label>
            <span className="sr-only">搜索商品</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="搜索商品"
            />
          </label>
          {query && (
            <button
              className="search-clear"
              type="button"
              onClick={() => setQuery('')}
              aria-label="清除搜索"
            >
              ×
            </button>
          )}
        </form>
      </header>
      <section className="hero" aria-roledescription="carousel" aria-label="精选活动轮播">
        <div className="hero-copy" aria-live="polite">
          <p className="eyebrow">{hero.eyebrow}</p>
          <h1 id="hero-title">{hero.title}</h1>
          <p>{hero.description}</p>
          <Link className="hero-action" to={`/product/${hero.productId}`}>
            {hero.action}
          </Link>
        </div>
        <div className="hero-controls">
          <button
            className="hero-control"
            type="button"
            onClick={() => moveSlide(-1)}
            aria-label="上一张轮播图"
          >
            ‹
          </button>
          <div className="hero-dots" role="tablist" aria-label="选择轮播图">
            {heroSlides.map((slide, index) => (
              <button
                className={index === activeSlide ? 'active' : ''}
                type="button"
                role="tab"
                aria-selected={index === activeSlide}
                aria-label={`查看第 ${index + 1} 张轮播图`}
                key={slide.title}
                onClick={() => setActiveSlide(index)}
              />
            ))}
          </div>
          <button
            className="hero-control"
            type="button"
            onClick={() => moveSlide(1)}
            aria-label="下一张轮播图"
          >
            ›
          </button>
        </div>
      </section>
      <section className="section" aria-labelledby="category-title">
        <div className="section-title">
          <h2 id="category-title">热门分类</h2>
          <Link className="text-action" to="/categories">
            查看全部
          </Link>
        </div>
        <div className="categories">
          {homeCategoryLabels.map((item) => (
            <Link className="category" to="/categories" key={item}>
              <span className="category-icon" aria-hidden="true">
                ✦
              </span>
              <span>{item}</span>
            </Link>
          ))}
        </div>
      </section>
      <section className="section activity" aria-label="活动专区">
        <div className="activity-copy">
          <p className="eyebrow">限时活动</p>
          <strong>
            春日好物
            <br />
            低至 7 折
          </strong>
        </div>
        <Link className="text-action" to="/categories">
          去看看
        </Link>
      </section>
      <section className="section" aria-labelledby="product-title">
        <div className="section-title">
          <h2 id="product-title">{query ? '搜索结果' : '人气好物'}</h2>
          <span>
            {productsQuery.isLoading ? '加载中' : query ? `${visibleProducts.length} 件` : '热销榜'}
          </span>
        </div>
        {productsQuery.isError ? (
          <ErrorState onRetry={() => void productsQuery.refetch()}>
            商品加载失败，请稍后重试
          </ErrorState>
        ) : visibleProducts.length === 0 ? (
          <div className="feedback">没有找到相关商品</div>
        ) : (
          <div className="product-grid">
            {visibleProducts.map((product, index) => (
              <Link className="product" to={`/product/${product.id}`} key={product.id}>
                <ProductCard product={{ ...product, imageIndex: index + 1 }} />
              </Link>
            ))}
          </div>
        )}
      </section>
      {query && (
        <p className="sr-only" role="status" aria-live="polite">
          找到 {visibleProducts.length} 件商品
        </p>
      )}
      <BottomTabBar />
    </main>
  );
}
