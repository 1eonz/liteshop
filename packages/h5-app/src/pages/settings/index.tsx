import type { JSX } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useSessionStore } from '../../store/session';

/** H5 账户设置页，保留可扩展的隐私、通知和退出入口。 */
export function SettingsPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  if (!authenticated) return <Navigate to="/login" state={{ from: '/settings' }} replace />;
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回
        </Link>
        <h1>账户设置</h1>
      </header>
      <section className="me-links" aria-label="账户设置选项">
        <Link to="/notifications">
          <span>通知设置</span>
          <span aria-hidden="true">›</span>
        </Link>
        <Link to="/addresses">
          <span>收货地址</span>
          <span aria-hidden="true">›</span>
        </Link>
        <a href="mailto:privacy@liteshop.local">
          <span>隐私与帮助</span>
          <span aria-hidden="true">›</span>
        </a>
      </section>
    </main>
  );
}
