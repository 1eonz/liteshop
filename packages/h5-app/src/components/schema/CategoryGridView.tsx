import type { JSX, CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { CategorySummary, StoreComponentSchema } from '@liteshop/shared-types';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useCategoriesQuery } from '../../features/catalog';
import { numberProp, pathProp, textProp } from './schema-props';

interface CategoryGridViewProps {
  component: StoreComponentSchema;
}

/** 分类板块按需加载的数据视图。 */
export function CategoryGridView({ component }: CategoryGridViewProps): JSX.Element {
  const query = useCategoriesQuery();
  if (query.isLoading) return <FeedbackState>分类加载中…</FeedbackState>;
  if (query.isError) {
    return <ErrorState onRetry={() => void query.refetch()}>分类加载失败，请重试。</ErrorState>;
  }
  const categories = query.data ?? [];
  if (!categories.length) {
    return <EmptyState title="暂无分类" description="请先在后台创建商品分类。" />;
  }
  const columns = Math.max(2, Math.min(6, Math.floor(numberProp(component, 'columns', 4))));
  const showAll = component.props.showAll !== false;
  const allHref = pathProp(component, 'allHref', '/categories');
  const categoryStyle = { '--schema-category-columns': columns } as CSSProperties;
  return (
    <section
      className="section schema-category-grid"
      aria-labelledby={`schema-category-title-${component.id}`}
    >
      <div className="section-title">
        <h2 id={`schema-category-title-${component.id}`}>
          {textProp(component, 'title', '热门分类')}
        </h2>
        {showAll ? (
          <Link className="text-action" to={allHref}>
            {textProp(component, 'allLabel', '查看全部')}
          </Link>
        ) : null}
      </div>
      <div className="categories" style={categoryStyle}>
        {categories.slice(0, 8).map((category: CategorySummary) => (
          <Link className="category" to={`/categories?categoryId=${category.id}`} key={category.id}>
            <span className="category-icon" aria-hidden="true">
              {category.icon || '✦'}
            </span>
            <span>{category.name}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
