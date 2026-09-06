import type { JSX } from 'react';

/** 路由分片加载期间保持与页面一致的尺寸，避免首屏布局跳动。 */
export function RouteFallback(): JSX.Element {
  return (
    <main className="trade-page" aria-live="polite" aria-busy="true">
      <p className="feedback">页面加载中…</p>
    </main>
  );
}
