import type { JSX } from 'react';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BottomTabBar } from '../../components/BottomTabBar';
import { ProductCard } from '../../components/ProductCard';
import { useProductsQuery } from '../../features/catalog/api/useProductsQuery';
import { isRecoverableApiError } from '../../service/http';
import { listCategories } from '../../service/products';

const demoCategories = ['新品', '家居', '服饰', '数码', '美妆', '食品', '运动', '礼物'];

/** 商品分类页面，保留分类筛选区和商品列表的独立视图层。 */
export function CategoriesPage(): JSX.Element {
  const [activeCategory, setActiveCategory] = useState('全部');
  const categoriesQuery = useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      try {
        const items = await listCategories();
        return items.length ? items.map((item) => item.name) : demoCategories;
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoCategories;
      }
    },
  });
  const productsQuery = useProductsQuery();
  const categoryNames = ['全部', ...(categoriesQuery.data ?? demoCategories)];
  const products = productsQuery.data?.items ?? [];
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/">
          ‹ 返回
        </Link>
        <h1>商品分类</h1>
      </header>
      <div className="category-tabs" role="tablist" aria-label="商品分类">
        {categoryNames.map((category) => (
          <button
            type="button"
            role="tab"
            aria-selected={category === activeCategory}
            className={category === activeCategory ? 'selected' : ''}
            key={category}
            onClick={() => setActiveCategory(category)}
          >
            {category}
          </button>
        ))}
      </div>
      <section className="section category-intro">
        <p className="eyebrow">精选好物</p>
        <h2>{activeCategory === '全部' ? '发现适合你的生活好物' : activeCategory}</h2>
        <p className="muted">按分类浏览，快速找到今天想要的东西。</p>
      </section>
      {productsQuery.isLoading ? (
        <p className="feedback">商品加载中…</p>
      ) : products.length ? (
        <section className="product-grid">
          {products.map((product, index) => (
            <Link className="product" to={`/product/${product.id}`} key={product.id}>
              <ProductCard product={{ ...product, imageIndex: index + 1 }} />
            </Link>
          ))}
        </section>
      ) : (
        <p className="feedback">这个分类还没有商品。</p>
      )}
      <BottomTabBar active="category" />
    </main>
  );
}
