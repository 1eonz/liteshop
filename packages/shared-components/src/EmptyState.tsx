'use client';

import type { JSX } from 'react';

export interface EmptyStateProps {
  title?: string;
  description?: string;
}

/** 空状态组件，使用语义化区域向辅助技术说明当前状态。 */
export function EmptyState({
  title = 'No content',
  description = 'There is nothing to display.',
}: EmptyStateProps): JSX.Element {
  return (
    <section className="liteshop-empty" role="status">
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
