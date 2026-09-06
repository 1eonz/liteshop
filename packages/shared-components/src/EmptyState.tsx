'use client';

import type { JSX } from 'react';

export interface EmptyStateProps {
  /** 状态标题，由调用方传入已翻译内容。 */
  title?: string;
  /** 状态描述，由调用方传入已翻译内容。 */
  description?: string;
}

/** 空状态组件，使用语义化区域向辅助技术说明当前状态。 */
export function EmptyState({ title, description }: EmptyStateProps): JSX.Element {
  return (
    <section className="liteshop-empty" role="status">
      {title ? <h2>{title}</h2> : null}
      {description ? <p>{description}</p> : null}
    </section>
  );
}
