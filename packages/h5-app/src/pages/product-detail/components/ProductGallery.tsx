import type { JSX } from 'react';

export const DETAIL_SLIDES = ['商品主图', '生活场景', '细节展示'];

interface ProductGalleryProps {
  productName: string;
  imageIndex: number;
  onMove: (offset: number) => void;
  onSelect: (index: number) => void;
}

/** 商品详情轮播，只负责图片位置和键盘可操作的切换控件。 */
export function ProductGallery({
  productName,
  imageIndex,
  onMove,
  onSelect,
}: ProductGalleryProps): JSX.Element {
  return (
    <div
      className={`detail-visual detail-visual-${imageIndex + 1}`}
      aria-label={`${productName} 商品图轮播`}
      role="region"
      aria-roledescription="carousel"
    >
      <button
        className="visual-control visual-control-prev"
        type="button"
        onClick={() => onMove(-1)}
        aria-label="上一张商品图"
      >
        ‹
      </button>
      <span aria-live="polite">{DETAIL_SLIDES[imageIndex]}</span>
      <button
        className="visual-control visual-control-next"
        type="button"
        onClick={() => onMove(1)}
        aria-label="下一张商品图"
      >
        ›
      </button>
      <div className="hero-dots" role="tablist" aria-label="选择商品图片">
        {DETAIL_SLIDES.map((slide, index) => (
          <button
            className={index === imageIndex ? 'active' : ''}
            type="button"
            role="tab"
            aria-selected={index === imageIndex}
            aria-label={`查看${slide}`}
            key={slide}
            onClick={() => onSelect(index)}
          />
        ))}
      </div>
    </div>
  );
}
