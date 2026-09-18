import type { JSX, KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useEffect, useRef } from 'react';
import type { ProductDetailResponse } from '@liteshop/shared-types';
import { formatPrice } from '@liteshop/shared-types';
import { ProductImage } from '../../../components/ProductImage';
import { messages } from '../../../i18n/messages';

interface SkuDrawerProps {
  open: boolean;
  product: ProductDetailResponse;
  selectedSku: ProductDetailResponse['skus'][number] | undefined;
  loading: boolean;
  onClose: () => void;
  onSelect: (skuId: number) => void;
  onConfirm: () => void;
}

/** SKU 抽屉，集中处理焦点回收、Escape 关闭和键盘循环。 */
export function SkuDrawer({
  open,
  product,
  selectedSku,
  loading,
  onClose,
  onSelect,
  onConfirm,
}: SkuDrawerProps): JSX.Element | null {
  const drawerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return undefined;
    const previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const closeOnEscape = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', closeOnEscape);
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    drawerRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.body.style.overflow = previousOverflow;
      previousFocus?.focus();
    };
  }, [onClose, open]);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLElement>): void => {
    if (event.key !== 'Tab') return;
    const focusable = drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled])');
    if (!focusable?.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === first || document.activeElement === drawerRef.current)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  if (!open) return null;
  return (
    <div className="drawer-layer">
      <button
        className="drawer-backdrop"
        type="button"
        tabIndex={-1}
        aria-label="关闭规格选择"
        onClick={onClose}
      />
      <aside
        ref={drawerRef}
        tabIndex={-1}
        className="sku-drawer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="sku-title"
        onKeyDown={handleKeyDown}
      >
        <div className="drawer-grabber" />
        <div className="drawer-header">
          <h2 id="sku-title">选择规格</h2>
          <button className="drawer-close" type="button" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="sku-summary">
          <ProductImage className="sku-summary__image" src={product.coverUrl} alt={product.name} />
          <div>
            <strong className="detail-price">{formatPrice(selectedSku?.priceCents ?? product.minPrice)}</strong>
            <p>{product.name}</p>
            <span className="muted">{messages.stock(selectedSku?.quantity ?? 0)}</span>
          </div>
        </div>
        <div className="sku-options" role="group" aria-label={messages.chooseSku}>
        {product.skus.map((sku) => (
          <button
            type="button"
            className={`sku-option${sku.skuId === selectedSku?.skuId ? ' selected' : ''}`}
            key={sku.skuId}
            onClick={() => onSelect(sku.skuId)}
            aria-pressed={sku.skuId === selectedSku?.skuId}
            disabled={loading || sku.quantity <= 0}
          >
            {sku.name}
            <span>{sku.quantity <= 0 ? messages.soldOut : formatPrice(sku.priceCents)}</span>
          </button>
        ))}
        </div>
        <button
          className="primary-action"
          type="button"
          onClick={onConfirm}
          disabled={loading || !selectedSku || selectedSku.quantity <= 0}
        >
          {loading ? '加入中…' : '确定'}
        </button>
      </aside>
    </div>
  );
}
