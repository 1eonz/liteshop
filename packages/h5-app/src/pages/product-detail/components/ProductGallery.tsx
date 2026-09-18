import type { JSX } from 'react';
import { useRef } from 'react';
import { ProductImage } from '../../../components/ProductImage';
import { messages } from '../../../i18n/messages';

interface ProductGalleryProps {
  productName: string;
  images: readonly string[];
  imageIndex: number;
  onMove: (offset: number) => void;
  onSelect: (index: number) => void;
}

/** 商品详情轮播，只负责图片位置和键盘可操作的切换控件。 */
export function ProductGallery({
  productName,
  images,
  imageIndex,
  onMove,
  onSelect,
}: ProductGalleryProps): JSX.Element {
  const touchStart = useRef<{ x: number; y: number } | null>(null);
  const activeIndex = Math.min(imageIndex, Math.max(0, images.length - 1));
  return (
    <div
      className="detail-visual"
      aria-label={messages.productGallery(productName)}
      role="region"
      aria-roledescription="carousel"
      onKeyDown={(event) => {
        if (images.length < 2 || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
        event.preventDefault();
        onMove(event.key === 'ArrowLeft' ? -1 : 1);
      }}
      onTouchStart={(event) => {
        const touch = event.touches[0];
        touchStart.current = touch ? { x: touch.clientX, y: touch.clientY } : null;
      }}
      onTouchEnd={(event) => {
        const start = touchStart.current;
        const touch = event.changedTouches[0];
        touchStart.current = null;
        if (!start || !touch || images.length < 2) return;
        const dx = touch.clientX - start.x;
        const dy = touch.clientY - start.y;
        if (Math.abs(dx) > 48 && Math.abs(dx) > Math.abs(dy) * 1.5) onMove(dx < 0 ? 1 : -1);
      }}
      onTouchCancel={() => { touchStart.current = null; }}
    >
      <ProductImage className="detail-visual__image" src={images[activeIndex]} alt={messages.productImage(productName, activeIndex + 1)} priority />
      {images.length > 1 ? <>
      <button
        className="visual-control visual-control-prev"
        type="button"
        onClick={() => onMove(-1)}
        aria-label={messages.imagePrevious}
      >
        ‹
      </button>
      <button
        className="visual-control visual-control-next"
        type="button"
        onClick={() => onMove(1)}
        aria-label={messages.imageNext}
      >
        ›
      </button>
      <div className="hero-dots" role="group" aria-label={messages.imageSelect}>
        {images.map((src, index) => (
          <button
            className={index === activeIndex ? 'active' : ''}
            type="button"
            aria-pressed={index === activeIndex}
            aria-label={messages.imagePosition(index + 1, images.length)}
            key={src}
            onClick={() => onSelect(index)}
          />
        ))}
      </div>
      <span className="detail-visual__counter" aria-live="polite">{activeIndex + 1} / {images.length}</span>
      </> : null}
    </div>
  );
}
