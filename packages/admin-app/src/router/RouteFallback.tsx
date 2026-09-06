import type { JSX } from 'react';

/** 后台页面分片加载期间保持稳定布局，避免内容跳动。 */
export function RouteFallback(): JSX.Element {
  return (
    <main className="admin-page" aria-live="polite" aria-busy="true">
      <p className="feedback">页面加载中…</p>
    </main>
  );
}
