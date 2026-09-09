import type { CSSProperties, JSX } from 'react';

export type SkeletonVariant = 'text' | 'rectangular' | 'circular';

export interface SkeletonProps {
  /** 骨架形状；text 适合行文本，rectangular 适合图片区块。 */
  variant?: SkeletonVariant;
  /** 宽度 token 或 CSS 长度，默认填满容器。 */
  width?: CSSProperties['width'];
  /** 高度 token 或 CSS 长度，text 默认使用一行高度。 */
  height?: CSSProperties['height'];
  /** 辅助技术可读的加载提示；传空字符串可将其设为装饰性。 */
  label?: string;
  /** 额外的宿主样式类名。 */
  className?: string;
}

/** 低布局偏移的加载占位块，动画会尊重 prefers-reduced-motion。 */
export function Skeleton({
  className,
  height,
  label = '正在加载',
  variant = 'text',
  width,
}: SkeletonProps): JSX.Element {
  const style = {
    '--ui-skeleton-width': width,
    '--ui-skeleton-height': height,
  } as CSSProperties;
  const classes = ['ui-kit-skeleton', `ui-kit-skeleton--${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return (
    <span
      aria-label={label || undefined}
      aria-hidden={label ? undefined : true}
      className={classes}
      role={label ? 'status' : undefined}
      style={style}
    />
  );
}
