'use client';

import type { ButtonHTMLAttributes, PropsWithChildren, JSX, ReactNode } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  loadingLabel?: ReactNode;
  variant?: 'primary' | 'secondary' | 'danger';
}

/** 共享按钮，写操作通过 loading 状态阻止重复提交。 */
export function Button({
  children,
  loading = false,
  loadingLabel = 'Loading…',
  variant = 'primary',
  disabled,
  className,
  type = 'button',
  ...props
}: PropsWithChildren<ButtonProps>): JSX.Element {
  return (
    <button
      {...props}
      type={type}
      className={`liteshop-button liteshop-button--${variant}${className ? ` ${className}` : ''}`}
      disabled={disabled || loading}
      aria-busy={loading}
    >
      {loading ? loadingLabel : children}
    </button>
  );
}
