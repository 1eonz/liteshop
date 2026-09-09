import type { ButtonHTMLAttributes, JSX, PropsWithChildren, ReactNode } from 'react';

/**
 * 基础按钮的视觉变体。
 * 组件只负责语义与样式，不内置业务提交逻辑；写操作的防抖由宿主应用处理。
 */
export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 按钮视觉变体，默认使用主操作样式。 */
  variant?: ButtonVariant;
  /** 加载期间禁用按钮，避免重复触发写操作。 */
  loading?: boolean;
  /** 加载期间可选的替代文案。 */
  loadingLabel?: ReactNode;
}

/** 可迁移的基础按钮，使用原生 button 保证键盘和表单语义。 */
export function Button({
  children,
  className,
  disabled,
  loading = false,
  loadingLabel,
  type = 'button',
  variant = 'primary',
  ...props
}: PropsWithChildren<ButtonProps>): JSX.Element {
  const classes = ['ui-kit-button', `ui-kit-button--${variant}`, className]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      {...props}
      className={classes}
      disabled={disabled || loading}
      type={type}
      aria-busy={loading || undefined}
    >
      {loading ? (loadingLabel ?? children) : children}
    </button>
  );
}
