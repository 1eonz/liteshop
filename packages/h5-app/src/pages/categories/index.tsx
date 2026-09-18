import type { JSX } from 'react';
import { Link } from 'react-router-dom';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { BottomTabBar } from '../../components/BottomTabBar';
import { ProductCard } from '../../components/ProductCard';
import { useProductsQuery } from '../../features/catalog/api/useProductsQuery';
import { useCategoriesQuery } from '../../features/catalog/api/useCategoriesQuery';
import { messages } from '../../i18n/messages';

/** 商品分类页面，保留分类筛选区和商品列表的独立视图层。 */
export function CategoriesPage(): JSX.Element {
  const categoriesQuery = useCategoriesQuery();
  const productsQuery = useProductsQuery();
  const products = productsQuery.data?.items ?? [];
  return (
    <main className="trade-page categories-page">
      <header className="trade-header">
        <Link className="back-link" to="/">
          ‹ 返回
        </Link>
        <h1>{messages.categories}</h1>
      </header>
      <Link className="catalog-search-link" to="/search">{messages.searchPlaceholder}<span>{messages.search}</span></Link>
      <div className="category-layout">
        <aside className="category-directory" aria-label={messages.categoryDirectory}>
          <p className="category-directory__active">{messages.allProducts}</p>
          <ul>{(categoriesQuery.data ?? []).map((category) => <li key={category.id}>{category.name}</li>)}</ul>
        </aside>
        <section className="category-results" aria-labelledby="catalog-title">
          <h2 id="catalog-title">{messages.allProducts}</h2>
          <p className="catalog-notice">{messages.categoryNotice}</p>
          {categoriesQuery.isError ? <ErrorState onRetry={() => void categoriesQuery.refetch()}>{messages.categoriesError}</ErrorState> : null}
      {productsQuery.isLoading ? (
        <FeedbackState>{messages.productLoading}</FeedbackState>
      ) : productsQuery.isError ? (
        <ErrorState onRetry={() => void productsQuery.refetch()}>{messages.productError}</ErrorState>
      ) : products.length ? (
        <section className="product-grid">
          {products.map((product, index) => (
            <Link className="product" to={`/product/${product.id}`} key={product.id}>
              <ProductCard product={{ ...product, imageIndex: index + 1 }} />
            </Link>
          ))}
        </section>
      ) : (
        <EmptyState title={messages.productEmpty} description={messages.productEmptyDescription} />
      )}
        </section>
      </div>
      <BottomTabBar active="category" />
    </main>
  );
}
