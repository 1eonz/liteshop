import type { JSX } from 'react';
import type { ProductSummary } from '@liteshop/shared-types';
import { formatPrice } from '../utils/format-price';

interface ProductCardProps {
  product: ProductSummary & { imageIndex?: number };
}

/** 商品卡片，只接收展示数据，不拥有业务状态。 */
export function ProductCard({ product }: ProductCardProps): JSX.Element {
  const imageClass = product.imageIndex
    ? `product-image product-image-${product.imageIndex}`
    : 'product-image';
  return (
    <article className="product-card">
      <div className={imageClass} aria-hidden="true">
        {product.coverUrl ? <img src={product.coverUrl} alt="" /> : null}
      </div>
      <h3>{product.name}</h3>
      <p>轻盈质感，日常陪伴</p>
      <div className="product-meta">
        <strong>{formatPrice(product.minPrice)}</strong>
        <span>已售 {product.salesCount}</span>
      </div>
    </article>
  );
}
