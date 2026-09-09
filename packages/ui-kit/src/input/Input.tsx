import { useId } from 'react';
import type { InputHTMLAttributes, JSX } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** 输入框标签；提供后会自动与 input 建立 for/id 关联。 */
  label?: string;
  /** 辅助说明，会通过 aria-describedby 与输入框关联。 */
  helpText?: string;
  /** 错误说明；存在时输入框会标记为 aria-invalid。 */
  error?: string;
}

/** 带标签、辅助说明和错误语义的基础输入框。 */
export function Input({
  'aria-describedby': ariaDescribedBy,
  className,
  error,
  helpText,
  id,
  label,
  ...props
}: InputProps): JSX.Element {
  const generatedId = useId();
  const inputId = id ?? `ui-input-${generatedId.replace(/:/g, '')}`;
  const helpId = helpText ? `${inputId}-help` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = [ariaDescribedBy, helpId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <label className="ui-kit-input-field" htmlFor={inputId}>
      {label ? <span className="ui-kit-input-label">{label}</span> : null}
      <input
        {...props}
        className={['ui-kit-input', className].filter(Boolean).join(' ')}
        id={inputId}
        aria-describedby={describedBy}
        aria-invalid={error ? true : undefined}
      />
      {helpText ? (
        <span className="ui-kit-input-help" id={helpId}>
          {helpText}
        </span>
      ) : null}
      {error ? (
        <span className="ui-kit-input-error" id={errorId} role="alert">
          {error}
        </span>
      ) : null}
    </label>
  );
}
