import type { JSX } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { BottomTabBar } from '../../components/BottomTabBar';
import { ProductCard } from '../../components/ProductCard';
import { useProductsQuery } from '../../hooks/useProductsQuery';
import { listServerFavoriteProductIds } from '../../service/favorites';
import { useQuery } from '@tanstack/react-query';

/** 收藏页面，登录用户读取服务端持久化收藏。 */
export function FavoritesPage(): JSX.Element {
  const authenticated = Boolean(window.localStorage.getItem('liteshop.accessToken'));
  const productsQuery = useProductsQuery();
  const favoritesQuery = useQuery({
    queryKey: ['favorites'],
    queryFn: listServerFavoriteProductIds,
    enabled: authenticated,
  });
  if (!authenticated)
    return <Navigate to="/login" state={{ from: '/favorites' }} replace />;
  if (favoritesQuery.isLoading)
    return (
      <main className="trade-page">
        <p className="feedback">收藏加载中…</p>
      </main>
    );
  if (favoritesQuery.isError)
    return (
      <main className="trade-page">
        <p className="feedback error-state" role="alert">
          收藏加载失败，请重试。
        </p>
        <button
          className="primary-action"
          type="button"
          onClick={() => void favoritesQuery.refetch()}
        >
          重试
        </button>
      </main>
    );
  const ids = favoritesQuery.data ?? [];
  const products = (productsQuery.data?.items ?? []).filter((product) => ids.includes(product.id));
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回
        </Link>
        <h1>我的收藏</h1>
      </header>
      {products.length ? (
        <div className="product-grid">
          {products.map((product, index) => (
            <Link className="product" to={`/product/${product.id}`} key={product.id}>
              <ProductCard product={{ ...product, imageIndex: index + 1 }} />
            </Link>
          ))}
        </div>
      ) : (
        <section className="empty-state">
          <div className="empty-illustration" aria-hidden="true">
            ♡
          </div>
          <h2>还没有收藏</h2>
          <Link className="primary-action inline-action" to="/">
            去发现好物
          </Link>
        </section>
      )}
      <BottomTabBar active="me" />
    </main>
  );
}
