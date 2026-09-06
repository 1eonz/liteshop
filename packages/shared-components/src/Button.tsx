'use client';

import type { ButtonHTMLAttributes, PropsWithChildren, JSX, ReactNode } from 'react';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 是否显示加载态并禁用按钮。 */
  loading?: boolean;
  /** 加载态文案，由调用方传入已翻译内容；未提供时保留按钮内容。 */
  loadingLabel?: ReactNode;
  /** 按钮视觉变体。 */
  variant?: 'primary' | 'secondary' | 'danger';
}

/** 共享按钮，写操作通过 loading 状态阻止重复提交。 */
export function Button({
  children,
  loading = false,
  loadingLabel,
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
      {loading ? (loadingLabel ?? children) : children}
    </button>
  );
}
