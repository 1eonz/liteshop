'use client';

import type { JSX } from 'react';

export interface ProductCardProps {
  name: string;
  priceCents: number;
  imageUrl?: string;
  salesCount?: number;
}

/** 商品卡片，价格字段固定使用整数分。 */
export function ProductCard({
  name,
  priceCents,
  imageUrl,
  salesCount = 0,
}: ProductCardProps): JSX.Element {
  return (
    <article className="liteshop-product-card">
      <div
        className="liteshop-product-card__image"
        style={imageUrl ? { backgroundImage: `url(${imageUrl})` } : undefined}
        aria-hidden="true"
      />
      <h3>{name}</h3>
      <p className="liteshop-product-card__price">¥{(priceCents / 100).toFixed(2)}</p>
      <small>已售 {salesCount}</small>
    </article>
  );
}
