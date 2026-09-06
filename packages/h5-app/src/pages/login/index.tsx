import type { FormEvent, JSX } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { login, sendSmsCode } from '../../service/auth';
import { useSessionStore } from '../../store/session';

interface LoginLocationState {
  from?: string;
}

/** 手机号登录页面，验证码发送和登录提交均使用防抖动作。 */
export function LoginPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const setAccessToken = useSessionStore((state) => state.setAccessToken);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [feedback, setFeedback] = useState('');
  const [sent, setSent] = useState(false);
  const [countdown, setCountdown] = useState(0);
  useEffect(() => {
    if (countdown <= 0) return undefined;
    const timer = window.setInterval(() => {
      setCountdown((current) => Math.max(0, current - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [countdown]);
  const [requestCode, sending] = useDebounceAction(async () => {
    if (countdown > 0) return;
    if (!/^1\d{10}$/.test(phone)) {
      setFeedback('请输入有效的手机号。');
      return;
    }
    setFeedback('');
    try {
      await sendSmsCode({ phone, purpose: 'LOGIN' });
      setSent(true);
      setCountdown(60);
      setFeedback('验证码已发送，开发环境验证码为 123456。');
    } catch {
      setFeedback('验证码发送失败，请稍后重试。');
    }
  }, 1000);
  const submitLogin = useCallback(async () => {
    if (!/^1\d{10}$/.test(phone) || !/^\d{6}$/.test(code)) {
      setFeedback('请输入手机号和 6 位验证码。');
      return;
    }
    setFeedback('');
    try {
      const result = await login({ phone, code });
      setAccessToken(result.accessToken);
      const target = (location.state as LoginLocationState | null)?.from ?? '/me';
      navigate(target, { replace: true });
    } catch {
      setFeedback('登录失败，请检查验证码后重试。');
    }
  }, [code, location.state, navigate, phone, setAccessToken]);
  const [submit, submitting] = useDebounceAction(submitLogin, 1000);
  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void submit();
  };
  return (
    <main className="trade-page auth-page">
      <header className="trade-header">
        <button className="back-link back-button" type="button" onClick={() => navigate(-1)}>
          ‹ 返回
        </button>
        <h1>登录 LiteShop</h1>
      </header>
      <section className="form-card">
        <p className="eyebrow">手机号登录</p>
        <h2>欢迎回来</h2>
        <p className="muted">登录后可同步购物车、订单和收货地址。</p>
        <form onSubmit={onSubmit}>
          <label>
            手机号
            <input
              inputMode="tel"
              autoComplete="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="请输入手机号"
            />
          </label>
          <label>
            验证码
            <div className="code-row">
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="6 位验证码"
                maxLength={6}
              />
              <button
                className="text-action code-action"
                type="button"
                disabled={sending || countdown > 0 || !phone}
                onClick={() => void requestCode()}
              >
                {sending
                  ? '发送中…'
                  : countdown > 0
                    ? `${countdown}s 后重发`
                    : sent
                      ? '重新发送'
                      : '获取验证码'}
              </button>
            </div>
          </label>
          {feedback && (
            <p className="feedback" role="status">
              {feedback}
            </p>
          )}
          <button className="primary-action form-submit" type="submit" disabled={submitting}>
            {submitting ? '登录中…' : '登录'}
          </button>
        </form>
      </section>
    </main>
  );
}
