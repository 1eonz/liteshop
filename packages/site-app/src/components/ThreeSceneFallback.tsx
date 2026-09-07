'use client';

import type { CSSProperties, JSX } from 'react';
import { useEffect, useMemo, useState } from 'react';
import { createHero3DConfig, shouldUse3DFallback } from '@liteshop/shared-3d-components';

interface ThreeSceneProps {
  title?: string;
  description?: string;
  fallbackUrl?: string;
  className?: string;
}

function useSceneCapability(): boolean {
  const [fallback, setFallback] = useState(true);
  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const navigatorWithMemory = navigator as Navigator & { deviceMemory?: number };
    setFallback(
      shouldUse3DFallback({
        isMobile: window.matchMedia('(max-width: 720px)').matches,
        hardwareConcurrency: navigator.hardwareConcurrency || 0,
        deviceMemoryGb: navigatorWithMemory.deviceMemory ?? null,
        reducedMotion: media.matches,
      }),
    );
    const onMotionChange = (event: MediaQueryListEvent): void => setFallback(event.matches);
    media.addEventListener?.('change', onMotionChange);
    return () => media.removeEventListener?.('change', onMotionChange);
  }, []);
  return fallback;
}

/** 轻量 Hero 3D 占位：未来可在不改变调用方的情况下替换为 R3F 实现。 */
export function Hero3DBackground({
  title = '空间化展示',
  description = '在支持的设备上呈现轻量动态背景。',
  fallbackUrl,
  className = '',
}: ThreeSceneProps): JSX.Element {
  const fallback = useSceneCapability();
  const config = useMemo(
    () => createHero3DConfig({ mobileFallbackUrl: fallbackUrl }),
    [fallbackUrl],
  );
  const style = {
    '--scene-speed': `${config.speed}s`,
    '--scene-opacity': config.opacity,
  } as CSSProperties;
  return (
    <section className={`site-scene-3d ${className}`} style={style} aria-label="3D 场景预览">
      {fallback && fallbackUrl ? (
        <img className="site-scene-3d__fallback" src={fallbackUrl} alt="" />
      ) : (
        <div className="site-scene-3d__mesh" aria-hidden="true" />
      )}
      <div className="site-container site-scene-3d__content">
        <p className="site-eyebrow">LITESHOP 3D</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </section>
  );
}

/** 产品 3D 预览：当前使用静态回退资源，不引入 Three.js，保证首屏预算。 */
export function Product3DViewer({
  title = '产品空间预览',
  description = '当前设备使用轻量化预览。',
  fallbackUrl,
  className = '',
}: ThreeSceneProps): JSX.Element {
  const fallback = useSceneCapability();
  return (
    <section className={`site-product-3d ${className}`} aria-label="产品 3D 预览">
      {fallback && fallbackUrl ? (
        <img src={fallbackUrl} alt="产品预览" />
      ) : (
        <div className="site-product-3d__placeholder" aria-hidden="true">
          360°
        </div>
      )}
      <div>
        <p className="site-eyebrow">PRODUCT VIEWER</p>
        <h2>{title}</h2>
        <p>{description}</p>
      </div>
    </section>
  );
}
