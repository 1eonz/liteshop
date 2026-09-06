import type { FormEvent, JSX } from 'react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { loginAdmin } from '../../service/auth';
import { useSessionStore } from '../../store/session';

/** 后台管理员登录页，开发环境复用短信登录接口。 */
export function AdminLoginPage(): JSX.Element {
  const navigate = useNavigate();
  const setAccessToken = useSessionStore((state) => state.setAccessToken);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const login = async (): Promise<void> => {
    try {
      const response = await loginAdmin({ phone, code });
      setAccessToken(response.accessToken);
      navigate('/', { replace: true });
    } catch {
      setError('登录失败，请检查手机号和验证码。');
    }
  };
  const [submit, submitting] = useDebounceAction(login, 800);
  const onSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void submit();
  };
  return (
    <main className="admin-login">
      <section className="form-card">
        <p className="eyebrow">LiteShop Admin</p>
        <h1>管理员登录</h1>
        <p className="muted">开发环境验证码为 123456。</p>
        <form onSubmit={onSubmit}>
          <label>
            手机号
            <input
              inputMode="tel"
              value={phone}
              onChange={(event) => setPhone(event.target.value)}
              placeholder="管理员手机号"
              required
            />
          </label>
          <label>
            验证码
            <input
              inputMode="numeric"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              placeholder="123456"
              maxLength={6}
              required
            />
          </label>
          {error && (
            <p className="feedback error-state" role="alert">
              {error}
            </p>
          )}
          <button className="primary-action form-submit" type="submit" disabled={submitting}>
            {submitting ? '登录中…' : '进入后台'}
          </button>
        </form>
      </section>
    </main>
  );
}
