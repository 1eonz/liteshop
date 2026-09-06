import type { JSX, PropsWithChildren } from 'react';

interface AdminShellProps extends PropsWithChildren {
  title: string;
  eyebrow: string;
}

/** 后台页面通用内容壳，后续页面按需复用。 */
export function AdminShell({ title, eyebrow, children }: AdminShellProps): JSX.Element {
  return (
    <main className="editor-page">
      <header>
        <div>
          <p>{eyebrow}</p>
          <h1>{title}</h1>
        </div>
      </header>
      {children}
    </main>
  );
}
