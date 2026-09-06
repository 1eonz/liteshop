import type { JSX } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { BottomTabBar } from '../../components/BottomTabBar';
import { listOrders } from '../../service/orders';
import { formatPrice } from '@liteshop/shared-types';
import { useSessionStore } from '../../store/session';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

const statusLabels: Record<string, string> = {
  PENDING_PAYMENT: '待付款',
  PAID: '待发货',
  SHIPPED: '配送中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
};

/** 用户订单列表，所有订单状态来自共享状态机枚举值。 */
export function OrdersPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const query = useQuery({
    queryKey: ['orders'],
    queryFn: () => listOrders(),
    enabled: authenticated,
  });
  if (!authenticated) return <Navigate to="/login" state={{ from: '/orders' }} replace />;
  if (query.isLoading)
    return (
      <main className="trade-page">
        <FeedbackState>订单加载中…</FeedbackState>
      </main>
    );
  if (query.isError)
    return (
      <main className="trade-page">
        <ErrorState onRetry={() => void query.refetch()}>订单加载失败，请刷新重试。</ErrorState>
      </main>
    );
  const orders = query.data?.items ?? [];
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回
        </Link>
        <h1>我的订单</h1>
      </header>
      {orders.length ? (
        <section className="order-cards">
          {orders.map((order) => (
            <Link className="order-card" to={`/orders/${order.id}`} key={order.id}>
              <div className="order-card-head">
                <strong>{order.orderNo}</strong>
                <span>{statusLabels[order.status] ?? order.status}</span>
              </div>
              <p className="muted">
                {order.items.map((item) => `${item.productName} × ${item.quantity}`).join('、') ||
                  '订单商品'}
              </p>
              <div className="order-card-foot">
                <time dateTime={order.createdAt}>
                  {new Date(order.createdAt).toLocaleDateString('zh-CN')}
                </time>
                <strong>{formatPrice(order.totalAmount)}</strong>
              </div>
            </Link>
          ))}
        </section>
      ) : (
        <section className="empty-state">
          <div className="empty-illustration" aria-hidden="true">
            □
          </div>
          <h2>还没有订单</h2>
          <Link className="primary-action inline-action" to="/">
            去逛逛
          </Link>
        </section>
      )}
      <BottomTabBar active="me" />
    </main>
  );
}
