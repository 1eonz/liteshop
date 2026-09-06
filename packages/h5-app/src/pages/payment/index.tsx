import type { JSX } from 'react';
import { useCallback, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { PaymentProvider } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { createPayment, getOrder } from '../../service/orders';
import { formatPrice } from '../../utils/format-price';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useSessionStore } from '../../store/session';

/** H5 支付页面，创建支付单后等待渠道 SDK 或沙箱回调接入。 */
export function PaymentPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const params = useParams<{ orderId: string }>();
  const orderId = Number(params.orderId);
  const navigate = useNavigate();
  const [provider, setProvider] = useState<PaymentProvider>(PaymentProvider.WECHAT);
  const [paymentId, setPaymentId] = useState<number | string | null>(null);
  const [error, setError] = useState('');
  const query = useQuery({
    queryKey: ['order', orderId],
    enabled: authenticated && Number.isInteger(orderId) && orderId > 0,
    queryFn: () => getOrder(orderId),
  });
  const startPayment = useCallback(async () => {
    if (!query.data) return;
    setError('');
    try {
      const payment = await createPayment(orderId, provider, query.data.totalAmount);
      setPaymentId(payment.id);
    } catch {
      setError('支付单创建失败，请返回订单详情重试。');
    }
  }, [orderId, provider, query.data]);
  const [pay, paying] = useDebounceAction(startPayment, 800);
  if (!authenticated) return <Navigate to="/login" state={{ from: '/payment' }} replace />;
  if (query.isLoading)
    return (
      <main className="trade-page">
        <FeedbackState>支付信息加载中…</FeedbackState>
      </main>
    );
  if (query.isError || !query.data)
    return (
      <main className="trade-page">
        <ErrorState>订单不存在或已失效。</ErrorState>
        <Link to="/orders">返回订单列表</Link>
      </main>
    );
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to={`/orders/${orderId}`}>
          ‹ 返回
        </Link>
        <h1>收银台</h1>
      </header>
      <section className="payment-card">
        <p className="eyebrow">订单 {query.data.orderNo}</p>
        <strong className="detail-price">{formatPrice(query.data.totalAmount)}</strong>
        <div className="payment-options">
          <button
            className={provider === PaymentProvider.WECHAT ? 'selected' : ''}
            type="button"
            onClick={() => setProvider(PaymentProvider.WECHAT)}
          >
            微信支付
          </button>
          <button
            className={provider === PaymentProvider.ALIPAY ? 'selected' : ''}
            type="button"
            onClick={() => setProvider(PaymentProvider.ALIPAY)}
          >
            支付宝
          </button>
        </div>
        {paymentId ? (
          <div className="feedback" role="status">
            <strong>支付单已创建</strong>
            <p>支付单号：{paymentId}</p>
            <p className="muted">开发环境等待回调，接入真实渠道后此处将跳转收银台。</p>
            <button
              className="secondary-action"
              type="button"
              onClick={() => navigate(`/orders/${orderId}`)}
            >
              返回订单
            </button>
          </div>
        ) : (
          <button
            className="primary-action wide-action"
            type="button"
            disabled={paying}
            onClick={() => void pay()}
          >
            {paying
              ? '创建支付单…'
              : `使用${provider === PaymentProvider.WECHAT ? '微信' : '支付宝'}支付`}
          </button>
        )}
        {error && (
          <p className="feedback error-state" role="alert">
            {error}
          </p>
        )}
      </section>
    </main>
  );
}
