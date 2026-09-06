import type { JSX, KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useEffect, useRef } from 'react';
import type { ProductDetailResponse } from '@liteshop/shared-types';
import { formatPrice } from '../../../utils/format-price';

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
    document.body.style.overflow = 'hidden';
    drawerRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.body.style.overflow = '';
      previousFocus?.focus();
    };
  }, [onClose, open]);

  const handleKeyDown = (event: ReactKeyboardEvent<HTMLElement>): void => {
    if (event.key !== 'Tab') return;
    const focusable = drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled])');
    if (!focusable?.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
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
        {product.skus.map((sku) => (
          <button
            type="button"
            className={`sku-option${sku.skuId === selectedSku?.skuId ? ' selected' : ''}`}
            key={sku.skuId}
            onClick={() => onSelect(sku.skuId)}
          >
            {sku.name}
            <span>{formatPrice(sku.priceCents)}</span>
          </button>
        ))}
        <button
          className="primary-action"
          type="button"
          onClick={onConfirm}
          disabled={loading || !selectedSku}
        >
          {loading ? '加入中…' : '确定'}
        </button>
      </aside>
    </div>
  );
}
