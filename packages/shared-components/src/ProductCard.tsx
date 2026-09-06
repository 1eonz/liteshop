'use client';

import type { JSX, ReactNode } from 'react';
import type { ProductSummary } from '@liteshop/shared-types';
import { formatPrice } from '@liteshop/shared-types';

interface ProductCardBaseProps {
  /** 可选的图片地址；未提供时使用主题占位背景。 */
  imageUrl?: string;
  /** 图片替代文本，装饰性图片可保持空字符串。 */
  imageAlt?: string;
  /** 商品副标题，由调用方传入已翻译内容。 */
  subtitle?: ReactNode;
  /** 销量标签，由调用方传入已翻译内容。 */
  salesLabel?: ReactNode;
  /** 货币符号或货币文本。 */
  currency?: string;
  /** 追加到根节点的样式类。 */
  className?: string;
}

export interface ProductCardFlatProps extends ProductCardBaseProps {
  /** 商品名称。 */
  name: string;
  /** 商品价格，单位为整数分。 */
  priceCents: number;
  /** 已售数量。 */
  salesCount?: number;
}

export interface ProductCardProductProps extends ProductCardBaseProps {
  /** 共享商品摘要模型，价格字段使用整数分。 */
  product: ProductSummary;
}

/** ProductCard 支持的两种数据输入。 */
export type ProductCardProps = ProductCardFlatProps | ProductCardProductProps;

/** 商品卡片，兼容扁平展示数据和共享商品摘要模型。 */
export function ProductCard({
  imageUrl,
  imageAlt = '',
  subtitle,
  salesLabel = 'Sold',
  currency = '¥',
  className,
  ...props
}: ProductCardProps): JSX.Element {
  const product = 'product' in props ? props.product : undefined;
  const name = product?.name ?? ('name' in props ? props.name : '');
  const priceCents = product?.minPrice ?? ('priceCents' in props ? props.priceCents : 0);
  const resolvedImageUrl = imageUrl ?? product?.coverUrl;
  const salesCount =
    product?.salesCount ?? ('salesCount' in props ? (props.salesCount ?? 0) : undefined);

  return (
    <article className={`liteshop-product-card${className ? ` ${className}` : ''}`}>
      <div
        className="liteshop-product-card__image"
        style={resolvedImageUrl ? { backgroundImage: `url(${resolvedImageUrl})` } : undefined}
        aria-label={imageAlt}
        role={resolvedImageUrl ? 'img' : undefined}
      />
      <h3>{name}</h3>
      {subtitle ? <p className="liteshop-product-card__subtitle">{subtitle}</p> : null}
      <p className="liteshop-product-card__price">{formatPrice(priceCents, currency)}</p>
      {salesCount !== undefined ? (
        <small className="liteshop-product-card__sales">
          {salesLabel} {salesCount}
        </small>
      ) : null}
    </article>
  );
}
