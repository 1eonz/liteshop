import type { JSX } from 'react';
import { useCallback, useState } from 'react';
import {
  useAdminOrderMutations,
  useAdminOrdersQuery,
  useDebounceAction,
  useShipAdminOrderMutation,
} from '../../hooks';
import { formatPrice } from '../../utils/format-price';

const statusLabels: Record<string, string> = {
  PENDING_PAYMENT: '待付款',
  PAID: '待发货',
  SHIPPED: '已发货',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
};

/** 订单列表页面，读取服务端订单并复用状态机执行发货。 */
export function OrdersPage(): JSX.Element {
  const ordersQuery = useAdminOrdersQuery();
  const shipMutation = useShipAdminOrderMutation();
  const orderMutations = useAdminOrderMutations();
  const [shippingOrderId, setShippingOrderId] = useState<number | null>(null);
  const [trackingNo, setTrackingNo] = useState('');
  const [shipError, setShipError] = useState('');
  const [editingOrderId, setEditingOrderId] = useState<number | null>(null);
  const [newPrice, setNewPrice] = useState('');
  const [remark, setRemark] = useState('');
  const ship = useCallback(
    async (orderId: number) => {
      setShipError('');
      if (!trackingNo.trim()) {
        setShipError('请输入物流单号。');
        return;
      }
      try {
        await shipMutation.mutateAsync({
          orderId,
          input: {
            logisticsCompanyCode: 'OTHER',
            trackingNo: trackingNo.trim(),
          },
        });
        setShippingOrderId(null);
        setTrackingNo('');
      } catch {
        setShipError('发货失败，请确认订单状态和物流单号后重试。');
      }
    },
    [shipMutation, trackingNo],
  );
  const [runShip, shipping] = useDebounceAction(ship, 500);
  const cancel = useCallback(
    async (orderId: number) => {
      setShipError('');
      try {
        await orderMutations.cancel.mutateAsync(orderId);
      } catch {
        setShipError('取消订单失败，请确认订单仍处于待付款状态。');
      }
    },
    [orderMutations.cancel],
  );
  const saveOrder = useCallback(
    async (orderId: number, allowPrice: boolean) => {
      setShipError('');
      const parsedPrice = allowPrice && newPrice.trim() ? Number(newPrice) : undefined;
      if (parsedPrice !== undefined && (!Number.isInteger(parsedPrice) || parsedPrice < 0)) {
        setShipError('改价必须填写非负整数分。');
        return;
      }
      try {
        if (parsedPrice !== undefined)
          await orderMutations.changePrice.mutateAsync({
            orderId,
            totalAmount: parsedPrice,
          });
        await orderMutations.update.mutateAsync({ orderId, input: { remark } });
        setEditingOrderId(null);
        setNewPrice('');
        setRemark('');
      } catch {
        setShipError('订单信息保存失败，请稍后重试。');
      }
    },
    [newPrice, orderMutations.changePrice, orderMutations.update, remark],
  );
  const [runCancel, cancelling] = useDebounceAction(cancel, 500);
  const [runSaveOrder, savingOrder] = useDebounceAction(saveOrder, 500);
  if (ordersQuery.isLoading)
    return (
      <div className="editor-page">
        <div className="feedback">订单加载中…</div>
      </div>
    );
  if (ordersQuery.isError)
    return (
      <div className="editor-page">
        <div className="feedback error-state" role="alert">
          订单加载失败，请刷新重试。
        </div>
      </div>
    );
  const orders = ordersQuery.data?.items ?? [];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>订单管理</p>
          <h1>订单列表</h1>
        </div>
        <button
          type="button"
          disabled={ordersQuery.isFetching}
          onClick={() => void ordersQuery.refetch()}
        >
          {ordersQuery.isFetching ? '刷新中…' : '刷新'}
        </button>
      </header>
      {shipError && (
        <p className="feedback error-state" role="alert">
          {shipError}
        </p>
      )}
      <section className="editor-form order-list" aria-label="订单列表">
        {orders.length ? (
          orders.map((order) => (
            <article className="order-row" key={order.id}>
              <div>
                <strong>{order.orderNo}</strong>
                <span className="muted">{statusLabels[order.status] ?? order.status}</span>
              </div>
              <span>
                {order.items.map((item) => `${item.productName} × ${item.quantity}`).join('、') ||
                  '无商品明细'}
              </span>
              <strong>{formatPrice(order.totalAmount)}</strong>
              <div className="row-actions">
                {order.status === 'PAID' &&
                  (shippingOrderId === order.id ? (
                    <div className="ship-form">
                      <input
                        aria-label="物流单号"
                        placeholder="物流单号"
                        value={trackingNo}
                        onChange={(event) => setTrackingNo(event.target.value)}
                      />
                      <button
                        type="button"
                        disabled={shipping}
                        onClick={() => void runShip(order.id)}
                      >
                        {shipping ? '提交中…' : '确认发货'}
                      </button>
                      <button
                        className="ghost-button"
                        type="button"
                        disabled={shipping}
                        onClick={() => setShippingOrderId(null)}
                      >
                        取消
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      disabled={shipping}
                      onClick={() => setShippingOrderId(order.id)}
                    >
                      发货
                    </button>
                  ))}
                {order.status === 'PENDING_PAYMENT' && (
                  <button
                    className="ghost-button"
                    type="button"
                    disabled={cancelling}
                    onClick={() => void runCancel(order.id)}
                  >
                    {cancelling ? '取消中…' : '取消'}
                  </button>
                )}
                <button
                  className="ghost-button"
                  type="button"
                  onClick={() => {
                    setEditingOrderId(order.id);
                    setRemark(order.remark ?? '');
                    setNewPrice(String(order.totalAmount));
                  }}
                >
                  备注/改价
                </button>
              </div>
              {editingOrderId === order.id && (
                <div className="ship-form">
                  <label>
                    订单备注
                    <input
                      aria-label="订单备注"
                      value={remark}
                      onChange={(event) => setRemark(event.target.value)}
                    />
                  </label>
                  {order.status === 'PENDING_PAYMENT' && (
                    <label>
                      金额（分）
                      <input
                        aria-label="订单金额"
                        inputMode="numeric"
                        value={newPrice}
                        onChange={(event) => setNewPrice(event.target.value)}
                      />
                    </label>
                  )}
                  <button
                    type="button"
                    disabled={savingOrder}
                    onClick={() => void runSaveOrder(order.id, order.status === 'PENDING_PAYMENT')}
                  >
                    {savingOrder ? '保存中…' : '保存'}
                  </button>
                  <button
                    className="ghost-button"
                    type="button"
                    disabled={savingOrder}
                    onClick={() => setEditingOrderId(null)}
                  >
                    取消
                  </button>
                </div>
              )}
            </article>
          ))
        ) : (
          <div className="feedback">暂无订单数据</div>
        )}
      </section>
    </div>
  );
}
