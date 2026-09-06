import type { JSX } from 'react';
import type { ProductSummary } from '@liteshop/shared-types';
import { ProductCard as SharedProductCard } from '@liteshop/shared-components';

interface ProductCardProps {
  product: ProductSummary & { imageIndex?: number };
}

/** 商品卡片，只接收展示数据，不拥有业务状态。 */
export function ProductCard({ product }: ProductCardProps): JSX.Element {
  const className = product.imageIndex ? `product-image-${product.imageIndex}` : undefined;
  return (
    <SharedProductCard
      product={product}
      className={className}
      subtitle="轻盈质感，日常陪伴"
      salesLabel="已售"
      imageAlt={product.name}
    />
  );
}
