import type { JSX } from 'react';
import { useCallback } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { cancelOrder, confirmOrder, getOrder } from '../../service/orders';
import { formatPrice } from '../../utils/format-price';

const statusLabels: Record<string, string> = {
  PENDING_PAYMENT: '待付款',
  PAID: '待发货',
  SHIPPED: '配送中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
};

/** 用户订单详情，取消和确认收货均通过状态机接口完成。 */
export function OrderDetailPage(): JSX.Element {
  const params = useParams<{ orderId: string }>();
  const orderId = Number(params.orderId);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['order', orderId],
    enabled: Number.isInteger(orderId) && orderId > 0,
    queryFn: () => getOrder(orderId),
  });
  const mutateOrder = useCallback(
    async (action: 'cancel' | 'confirm') => {
      if (!query.data) return;
      const next = action === 'cancel' ? await cancelOrder(orderId) : await confirmOrder(orderId);
      queryClient.setQueryData(['order', orderId], next);
      void queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
    [orderId, query.data, queryClient],
  );
  const [runCancel, cancelling] = useDebounceAction(() => mutateOrder('cancel'), 500);
  const [runConfirm, confirming] = useDebounceAction(() => mutateOrder('confirm'), 500);
  if (query.isLoading)
    return (
      <main className="trade-page">
        <p className="feedback">订单加载中…</p>
      </main>
    );
  if (query.isError || !query.data)
    return (
      <main className="trade-page">
        <p className="feedback error-state" role="alert">
          订单不存在或加载失败。
        </p>
        <Link to="/orders">返回订单列表</Link>
      </main>
    );
  const order = query.data;
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/orders">
          ‹ 返回
        </Link>
        <h1>订单详情</h1>
      </header>
      <section className="order-status-card">
        <span className="eyebrow">订单状态</span>
        <strong>{statusLabels[order.status] ?? order.status}</strong>
        <p className="muted">订单号 {order.orderNo}</p>
      </section>
      <section className="address-card">
        <h2>收货地址</h2>
        <p>
          <strong>{order.addressSnapshot.receiverName ?? '收货人'}</strong>{' '}
          {order.addressSnapshot.phone ?? ''}
        </p>
        <p className="muted">{order.addressSnapshot.detail ?? '地址快照'}</p>
      </section>
      <section className="checkout-items">
        <h2>商品清单</h2>
        {order.items.map((item) => (
          <article className="cart-item" key={item.id}>
            <div className="cart-thumb" aria-hidden="true" />
            <div className="cart-line-content">
              <h3>{item.productName}</h3>
              <p className="muted">
                {item.skuName} × {item.quantity}
              </p>
            </div>
            <strong>{formatPrice(item.totalAmount)}</strong>
          </article>
        ))}
      </section>
      <div className="summary-row">
        <span>商品金额</span>
        <span>{formatPrice(order.productAmount)}</span>
      </div>
      <div className="summary-row">
        <span>运费</span>
        <span>{formatPrice(order.freightAmount)}</span>
      </div>
      <div className="summary-row total-row">
        <strong>合计</strong>
        <strong>{formatPrice(order.totalAmount)}</strong>
      </div>
      {order.trackingNo && <p className="feedback">物流单号：{order.trackingNo}</p>}
      <div className="order-actions">
        {order.status === 'PENDING_PAYMENT' && (
          <>
            <Link className="secondary-action" to={`/payment/${order.id}`}>
              去支付
            </Link>
            <button
              className="secondary-action"
              type="button"
              disabled={cancelling}
              onClick={() => void runCancel()}
            >
              {cancelling ? '取消中…' : '取消订单'}
            </button>
          </>
        )}
        {order.status === 'SHIPPED' && (
          <button
            className="primary-action"
            type="button"
            disabled={confirming}
            onClick={() => void runConfirm()}
          >
            {confirming ? '确认中…' : '确认收货'}
          </button>
        )}
      </div>
    </main>
  );
}
