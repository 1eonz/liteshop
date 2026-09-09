import type { JSX, ReactNode } from 'react';

export interface EmptyStateProps {
  /** 空状态标题；应使用调用方的本地化文案。 */
  title?: ReactNode;
  /** 空状态说明；应告诉用户当前状态和下一步。 */
  description?: ReactNode;
  /** 可选的恢复动作，例如“重新加载”或“去添加”。 */
  action?: ReactNode;
  /** 额外的宿主样式类名。 */
  className?: string;
}

/** 统一的列表/内容空状态，提供 status 语义和可选恢复动作。 */
export function EmptyState({
  action,
  className,
  description,
  title,
}: EmptyStateProps): JSX.Element {
  const classes = ['ui-kit-empty-state', className].filter(Boolean).join(' ');

  return (
    <section className={classes}>
      <div aria-live="polite" className="ui-kit-empty-state__content" role="status">
        {title ? <h2 className="ui-kit-empty-state__title">{title}</h2> : null}
        {description ? <p className="ui-kit-empty-state__description">{description}</p> : null}
      </div>
      {action ? <div className="ui-kit-empty-state__action">{action}</div> : null}
    </section>
  );
}
