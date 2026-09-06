import type { JSX } from 'react';
import type { CartItem } from '@liteshop/shared-types';
import { formatPrice } from '@liteshop/shared-types';

interface CartLineItemProps {
  line: CartItem;
  selected: boolean;
  changing: boolean;
  removing: boolean;
  onToggleSelected: (selected: boolean) => void;
  onChangeQuantity: (quantity: number) => void;
  onRemove: () => void;
}

/** 购物车商品行，封装选择、数量和删除三个局部交互。 */
export function CartLineItem({
  line,
  selected,
  changing,
  removing,
  onToggleSelected,
  onChangeQuantity,
  onRemove,
}: CartLineItemProps): JSX.Element {
  return (
    <article className="cart-item">
      <input
        type="checkbox"
        checked={selected}
        onChange={(event) => onToggleSelected(event.target.checked)}
        aria-label={`选择商品 ${line.name}`}
      />
      <div className="cart-thumb" aria-hidden="true" />
      <div className="cart-line-content">
        <h2>{line.name}</h2>
        <p className="muted">{line.skuCode}</p>
        <strong>{formatPrice(line.priceCents)}</strong>
      </div>
      <div className="quantity-control">
        <button
          type="button"
          onClick={() => onChangeQuantity(Math.max(1, line.quantity - 1))}
          disabled={changing || line.quantity <= 1}
          aria-label="减少数量"
        >
          −
        </button>
        <span>{line.quantity}</span>
        <button
          type="button"
          onClick={() => onChangeQuantity(line.quantity + 1)}
          disabled={changing}
          aria-label="增加数量"
        >
          ＋
        </button>
      </div>
      <button
        className="icon-action"
        type="button"
        onClick={onRemove}
        disabled={removing}
        aria-label={`删除 ${line.name}`}
      >
        ×
      </button>
    </article>
  );
}
