import type { JSX } from 'react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAdminProductsQuery } from '../../hooks';
import { formatPrice } from '../../utils/format-price';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

const statusLabels: Record<string, string> = {
  DRAFT: '草稿',
  ON_SHELF: '已上架',
  OFF_SHELF: '已下架',
};

/** 商品列表页面，编辑入口与 SPU 路由保持一致。 */
export function ProductsPage(): JSX.Element {
  const [keyword, setKeyword] = useState('');
  const query = useAdminProductsQuery({ q: keyword || undefined });
  if (query.isLoading)
    return (
      <div className="editor-page">
        <FeedbackState>商品加载中…</FeedbackState>
      </div>
    );
  if (query.isError)
    return (
      <div className="editor-page">
        <ErrorState onRetry={() => void query.refetch()}>商品加载失败，请刷新重试。</ErrorState>
      </div>
    );
  const products = query.data?.items ?? [];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>商品中心</p>
          <h1>商品管理</h1>
        </div>
        <Link className="primary-action" to="/products/edit">
          新建商品
        </Link>
      </header>
      <div className="toolbar">
        <label className="toolbar-search">
          搜索商品
          <input
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="名称关键词"
          />
          {keyword && (
            <button
              className="search-clear"
              type="button"
              onClick={() => setKeyword('')}
              aria-label="清除商品搜索"
            >
              ×
            </button>
          )}
        </label>
        <button type="button" disabled={query.isFetching} onClick={() => void query.refetch()}>
          {query.isFetching ? '刷新中…' : '刷新'}
        </button>
      </div>
      <p className="list-status" role="status" aria-live="polite">
        {query.isFetching ? '商品列表更新中…' : `当前显示 ${products.length} 件商品`}
      </p>
      <section className="editor-form product-list" aria-label="商品列表">
        {products.length ? (
          products.map((product) => (
            <Link
              className="admin-product-row"
              to={`/products/edit/${product.id}`}
              key={product.id}
            >
              <div>
                <strong>{product.name}</strong>
                <span className="muted">{statusLabels[product.status] ?? product.status}</span>
              </div>
              <span>
                {formatPrice(product.minPrice)}
                {product.minPrice !== product.maxPrice ? ` - ${formatPrice(product.maxPrice)}` : ''}
              </span>
              <span>{product.salesCount} 件销量</span>
              <span aria-hidden="true">›</span>
            </Link>
          ))
        ) : (
          <div className="feedback">暂无商品</div>
        )}
      </section>
    </div>
  );
}
