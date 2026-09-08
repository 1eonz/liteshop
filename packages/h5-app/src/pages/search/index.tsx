import type { FormEvent, JSX } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ProductCard } from '../../components/ProductCard';
import { BottomTabBar } from '../../components/BottomTabBar';
import { useProductsQuery } from '../../features/catalog/api/useProductsQuery';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

const HISTORY_KEY = 'liteshop.search.history';
const HOT_SEARCHES = ['保温杯', '收纳', '通勤包', '香氛'];

function readHistory(): string[] {
  try {
    const parsed: unknown = JSON.parse(window.localStorage.getItem(HISTORY_KEY) ?? '[]');
    return Array.isArray(parsed)
      ? parsed.filter((item): item is string => typeof item === 'string').slice(0, 8)
      : [];
  } catch {
    return [];
  }
}

/** 独立搜索页，历史记录只保存在当前用户设备并支持一键清理。 */
export function SearchPage(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [value, setValue] = useState(searchParams.get('q') ?? '');
  const [history, setHistory] = useState<string[]>(readHistory);
  const queryValue = searchParams.get('q')?.trim() ?? '';
  const productsQuery = useProductsQuery({ q: queryValue || undefined });

  useEffect(() => {
    setValue(queryValue);
  }, [queryValue]);

  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const next = value.trim();
    if (next) {
      const nextHistory = [next, ...history.filter((item) => item !== next)].slice(0, 8);
      setHistory(nextHistory);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory));
    }
    setSearchParams(next ? { q: next } : {});
  };

  const products = useMemo(() => productsQuery.data?.items ?? [], [productsQuery.data]);
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/">
          ‹ 返回
        </Link>
        <h1>搜索商品</h1>
      </header>
      <form className="search-field search-page__form" role="search" onSubmit={submit}>
        <label>
          <span className="sr-only">搜索商品</span>
          <input
            value={value}
            onChange={(event) => setValue(event.target.value)}
            placeholder="搜索商品名称"
          />
        </label>
        <button className="primary-action" type="submit">
          搜索
        </button>
      </form>
      {!queryValue && (
        <section className="search-page__suggestions">
          <div className="section-title">
            <h2>热门搜索</h2>
          </div>
          <div className="category-tabs">
            {HOT_SEARCHES.map((item) => (
              <button key={item} type="button" onClick={() => setSearchParams({ q: item })}>
                {item}
              </button>
            ))}
          </div>
          <div className="section-title">
            <h2>搜索历史</h2>
            {history.length > 0 && (
              <button
                className="text-action"
                type="button"
                onClick={() => {
                  setHistory([]);
                  window.localStorage.removeItem(HISTORY_KEY);
                }}
              >
                清空
              </button>
            )}
          </div>
          {history.length ? (
            <div className="category-tabs">
              {history.map((item) => (
                <button key={item} type="button" onClick={() => setSearchParams({ q: item })}>
                  {item}
                </button>
              ))}
            </div>
          ) : (
            <p className="muted">暂无搜索记录</p>
          )}
        </section>
      )}
      {queryValue && (
        <section className="section search-page__results" aria-labelledby="search-results-title">
          <div className="section-title">
            <h2 id="search-results-title">“{queryValue}”的搜索结果</h2>
            <span>{products.length} 件</span>
          </div>
          {productsQuery.isLoading && <FeedbackState>商品加载中…</FeedbackState>}
          {productsQuery.isError && (
            <ErrorState onRetry={() => void productsQuery.refetch()}>搜索失败，请重试。</ErrorState>
          )}
          {!productsQuery.isLoading && !productsQuery.isError && products.length === 0 && (
            <p className="feedback">没有找到相关商品。</p>
          )}
          <div className="product-grid">
            {products.map((product, index) => (
              <Link className="product" to={`/product/${product.id}`} key={product.id}>
                <ProductCard product={{ ...product, imageIndex: index + 1 }} />
              </Link>
            ))}
          </div>
        </section>
      )}
      <BottomTabBar />
    </main>
  );
}
