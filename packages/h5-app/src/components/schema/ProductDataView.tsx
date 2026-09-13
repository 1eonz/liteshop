import type { JSX, CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { StoreComponentSchema } from '@liteshop/shared-types';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { ProductCard } from '../ProductCard';
import { useProductsQuery } from '../../features/catalog';
import {
  schemaProductPageSize,
  selectSchemaProducts,
} from '../../features/catalog/model/schema-products';
import { numberProp, pathProp, textProp } from './schema-props';

interface ProductDataViewProps {
  component: StoreComponentSchema;
}

/** 商品板块按需加载的数据视图，统一消费 Schema 查询配置。 */
export function ProductDataView({ component }: ProductDataViewProps): JSX.Element {
  const count = Math.max(1, Math.min(24, Math.floor(numberProp(component, 'count', 6))));
  const query = useProductsQuery({ pageSize: schemaProductPageSize(component, count) });
  if (query.isLoading) return <FeedbackState>商品加载中…</FeedbackState>;
  if (query.isError) {
    return <ErrorState onRetry={() => void query.refetch()}>商品加载失败，请重试。</ErrorState>;
  }
  const products = selectSchemaProducts(component, query.data?.items ?? [], count);
  if (!products.length) {
    return <EmptyState title="暂无商品" description="请先发布商品，首页会自动展示。" />;
  }
  const isCarousel = component.type === 'ProductCarousel';
  const columns = Math.max(1, Math.min(4, Math.floor(numberProp(component, 'columns', 2))));
  const showAll = component.props.showAll !== false;
  const allHref = pathProp(component, 'allHref', '/categories');
  return (
    <section
      className={isCarousel ? 'section schema-product-carousel' : 'section'}
      aria-labelledby={`schema-product-${component.id}`}
    >
      <div className="section-title">
        <div>
          <p className="eyebrow">{textProp(component, 'eyebrow', '商品列表')}</p>
          <h2 id={`schema-product-${component.id}`}>{textProp(component, 'title', '精选商品')}</h2>
        </div>
        {showAll ? (
          <Link className="text-action" to={allHref}>
            {textProp(component, 'allLabel', '查看全部')}
          </Link>
        ) : null}
      </div>
      <div
        className={isCarousel ? 'schema-product-carousel__track' : 'product-grid'}
        style={isCarousel ? undefined : ({ '--schema-product-columns': columns } as CSSProperties)}
      >
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
