'use client';

import type { JSX, ReactNode } from 'react';

export interface FeedbackStateProps {
  children: ReactNode;
  role?: 'status' | 'alert';
  className?: string;
}

/** 统一承载页面加载、错误和操作反馈，保持语义角色一致。 */
export function FeedbackState({
  children,
  role = 'status',
  className = 'feedback',
}: FeedbackStateProps): JSX.Element {
  return (
    <p className={className} role={role}>
      {children}
    </p>
  );
}

export interface ErrorStateProps {
  children: ReactNode;
  onRetry?: () => void;
  /** 重试按钮文案，由调用方传入已翻译内容。 */
  retryLabel?: ReactNode;
}

/** 错误状态统一提供可选的重试动作，避免页面静默失败。 */
export function ErrorState({
  children,
  onRetry,
  retryLabel = 'Retry',
}: ErrorStateProps): JSX.Element {
  return (
    <div className="feedback-group">
      <FeedbackState role="alert" className="feedback error-state">
        {children}
      </FeedbackState>
      {onRetry && (
        <button className="primary-action" type="button" onClick={onRetry}>
          {retryLabel}
        </button>
      )}
    </div>
  );
}
