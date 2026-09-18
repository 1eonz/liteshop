import type { JSX } from 'react';
import { useState } from 'react';
import { messages } from '../i18n/messages';

interface ProductImageProps {
  src?: string;
  alt: string;
  className?: string;
  priority?: boolean;
}

/** 真实商品图片及断图回退，预留尺寸由宿主样式控制。 */
export function ProductImage({ src, alt, className, priority = false }: ProductImageProps): JSX.Element {
  const [failedUrl, setFailedUrl] = useState<string>();
  return src && failedUrl !== src ? (
    <img
      className={className}
      src={src}
      alt={alt}
      loading={priority ? 'eager' : 'lazy'}
      decoding="async"
      onError={() => setFailedUrl(src)}
    />
  ) : (
    <span className={className ? `${className} image-unavailable` : 'image-unavailable'}>
      {messages.imageUnavailable}
    </span>
  );
}
