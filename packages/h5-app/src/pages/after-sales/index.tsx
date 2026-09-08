import type { JSX } from 'react';
import { useState } from 'react';
import { Link, useSearchParams, useParams, Navigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AfterSaleStatus,
  AfterSaleType,
  formatPrice,
  type AfterSaleCreateInput,
} from '@liteshop/shared-types';
import { ErrorState, EmptyState, FeedbackState } from '@liteshop/shared-components';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import {
  createAfterSale,
  getAfterSale,
  listAfterSales,
  submitAfterSaleReturn,
} from '../../service/after-sales';
import { useSessionStore } from '../../store/session';

const statusLabels: Record<AfterSaleStatus, string> = {
  [AfterSaleStatus.PENDING_REVIEW]: '待审核',
  [AfterSaleStatus.APPROVED]: '已同意',
  [AfterSaleStatus.REJECTED]: '已拒绝',
  [AfterSaleStatus.WAITING_RETURN]: '待寄回',
  [AfterSaleStatus.RETURNED]: '待验收',
  [AfterSaleStatus.REFUNDING]: '退款中',
  [AfterSaleStatus.COMPLETED]: '已完成',
  [AfterSaleStatus.CANCELLED]: '已关闭',
};

const typeLabels: Record<AfterSaleType, string> = {
  [AfterSaleType.REFUND_ONLY]: '仅退款',
  [AfterSaleType.RETURN_REFUND]: '退货退款',
  [AfterSaleType.EXCHANGE]: '换货',
};

interface AfterSaleFormProps {
  defaultOrderItemId: number;
  defaultAmountCents: number;
  onCreated: (record: { id: number }) => void;
}

function AfterSaleForm({
  defaultOrderItemId,
  defaultAmountCents,
  onCreated,
}: AfterSaleFormProps): JSX.Element {
  const queryClient = useQueryClient();
  const [orderItemId, setOrderItemId] = useState(String(defaultOrderItemId || ''));
  const [amountCents, setAmountCents] = useState(String(defaultAmountCents || ''));
  const [type, setType] = useState<AfterSaleType>(AfterSaleType.REFUND_ONLY);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');
  const mutation = useMutation({
    mutationFn: (input: AfterSaleCreateInput) => createAfterSale(input),
    retry: 0,
    onSuccess: (record) => {
      void queryClient.invalidateQueries({ queryKey: ['after-sales'] });
      onCreated(record);
    },
  });
  const submit = async (): Promise<void> => {
    const parsedOrderItemId = Number(orderItemId);
    const parsedAmount = Number(amountCents);
    if (!Number.isInteger(parsedOrderItemId) || parsedOrderItemId <= 0) {
      setError('请输入有效的订单商品编号。');
      return;
    }
    if (!Number.isInteger(parsedAmount) || parsedAmount <= 0) {
      setError('申请金额必须是正整数分。');
      return;
    }
    if (!reason.trim()) {
      setError('请填写售后原因。');
      return;
    }
    setError('');
    try {
      await mutation.mutateAsync({
        orderItemId: parsedOrderItemId,
        amountCents: parsedAmount,
        type,
        reason: reason.trim(),
      });
    } catch {
      setError('售后申请提交失败，请确认订单状态和金额后重试。');
    }
  };
  const [runSubmit, submitting] = useDebounceAction(submit, 800);
  return (
    <section className="after-sale-form" aria-labelledby="after-sale-form-title">
      <h2 id="after-sale-form-title">申请售后</h2>
      <div className="form-grid">
        <label>
          订单商品编号
          <input
            inputMode="numeric"
            value={orderItemId}
            onChange={(event) => setOrderItemId(event.target.value)}
          />
        </label>
        <label>
          申请金额（分）
          <input
            inputMode="numeric"
            value={amountCents}
            onChange={(event) => setAmountCents(event.target.value)}
          />
        </label>
      </div>
      <label>
        售后类型
        <select value={type} onChange={(event) => setType(event.target.value as AfterSaleType)}>
          {Object.values(AfterSaleType).map((value) => (
            <option value={value} key={value}>
              {typeLabels[value]}
            </option>
          ))}
        </select>
      </label>
      <label>
        售后原因
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} />
      </label>
      {error && (
        <FeedbackState role="alert" className="feedback error-state">
          {error}
        </FeedbackState>
      )}
      <button
        className="primary-action"
        type="button"
        disabled={submitting}
        onClick={() => void runSubmit()}
      >
        {submitting ? '提交中…' : '提交申请'}
      </button>
    </section>
  );
}

function AfterSaleDetailPage({ afterSaleId }: { afterSaleId: number }): JSX.Element {
  const queryClient = useQueryClient();
  const [trackingNo, setTrackingNo] = useState('');
  const [error, setError] = useState('');
  const query = useQuery({
    queryKey: ['after-sale', afterSaleId],
    queryFn: () => getAfterSale(afterSaleId),
    enabled: Number.isInteger(afterSaleId) && afterSaleId > 0,
  });
  const mutation = useMutation({
    mutationFn: () => submitAfterSaleReturn(afterSaleId, trackingNo.trim()),
    retry: 0,
    onSuccess: (record) => {
      queryClient.setQueryData(['after-sale', afterSaleId], record);
      void queryClient.invalidateQueries({ queryKey: ['after-sales'] });
    },
  });
  const submitReturn = async (): Promise<void> => {
    if (!trackingNo.trim()) {
      setError('请输入退货物流单号。');
      return;
    }
    setError('');
    try {
      await mutation.mutateAsync();
    } catch {
      setError('物流提交失败，请确认当前状态后重试。');
    }
  };
  const [runSubmitReturn, submitting] = useDebounceAction(submitReturn, 500);
  if (query.isLoading) return <FeedbackState>售后详情加载中…</FeedbackState>;
  if (query.isError || !query.data) {
    return <ErrorState onRetry={() => void query.refetch()}>售后单不存在或加载失败。</ErrorState>;
  }
  const record = query.data;
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/after-sales">
          ‹ 返回售后列表
        </Link>
        <h1>售后详情</h1>
      </header>
      <section className="order-status-card">
        <span className="eyebrow">{typeLabels[record.type]}</span>
        <strong>{statusLabels[record.status] ?? record.status}</strong>
        <p className="muted">售后单号 {record.afterSaleNo}</p>
      </section>
      <section className="address-card">
        <h2>申请信息</h2>
        <p>申请金额：{formatPrice(record.amountCents)}</p>
        <p className="muted">{record.reason}</p>
        {record.auditReason && <p className="feedback">审核备注：{record.auditReason}</p>}
      </section>
      {record.status === AfterSaleStatus.WAITING_RETURN && (
        <section className="after-sale-form" aria-labelledby="return-title">
          <h2 id="return-title">提交退货物流</h2>
          <label>
            物流单号
            <input value={trackingNo} onChange={(event) => setTrackingNo(event.target.value)} />
          </label>
          {error && (
            <FeedbackState role="alert" className="feedback error-state">
              {error}
            </FeedbackState>
          )}
          <button
            className="primary-action"
            type="button"
            disabled={submitting}
            onClick={() => void runSubmitReturn()}
          >
            {submitting ? '提交中…' : '提交物流'}
          </button>
        </section>
      )}
      {record.returnTrackingNo && <p className="feedback">退货物流：{record.returnTrackingNo}</p>}
    </main>
  );
}

/** H5 售后列表与申请入口，详情通过同一路由参数渲染。 */
export function AfterSalesPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const params = useParams<{ afterSaleId?: string }>();
  const [searchParams] = useSearchParams();
  if (!authenticated) return <Navigate to="/login" state={{ from: '/after-sales' }} replace />;
  if (params.afterSaleId) return <AfterSaleDetailPage afterSaleId={Number(params.afterSaleId)} />;
  const orderItemId = Number(searchParams.get('orderItemId') ?? '');
  const amountCents = Number(searchParams.get('amountCents') ?? '');
  return <AfterSaleList orderItemId={orderItemId} amountCents={amountCents} />;
}

function AfterSaleList({
  orderItemId,
  amountCents,
}: {
  orderItemId: number;
  amountCents: number;
}): JSX.Element {
  const [createdId, setCreatedId] = useState<number | null>(null);
  const query = useQuery({ queryKey: ['after-sales'], queryFn: listAfterSales });
  if (query.isLoading) return <FeedbackState>售后记录加载中…</FeedbackState>;
  if (query.isError)
    return <ErrorState onRetry={() => void query.refetch()}>售后记录加载失败，请重试。</ErrorState>;
  const items = query.data ?? [];
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回我的
        </Link>
        <h1>售后服务</h1>
      </header>
      {createdId && <FeedbackState>申请已提交，售后单号 #{createdId}。</FeedbackState>}
      <AfterSaleForm
        defaultOrderItemId={Number.isInteger(orderItemId) ? orderItemId : 0}
        defaultAmountCents={Number.isInteger(amountCents) ? amountCents : 0}
        onCreated={(record) => setCreatedId(record.id)}
      />
      <section className="after-sale-list" aria-labelledby="after-sale-list-title">
        <h2 id="after-sale-list-title">我的售后记录</h2>
        {items.length === 0 ? (
          <EmptyState title="暂无售后记录" description="订单出现问题时，可从订单详情发起售后。" />
        ) : (
          items.map((item) => (
            <Link className="after-sale-row" to={`/after-sales/${item.id}`} key={item.id}>
              <div>
                <strong>{typeLabels[item.type]}</strong>
                <span className="muted">{item.reason}</span>
              </div>
              <div>
                <strong>{formatPrice(item.amountCents)}</strong>
                <span className="muted">{statusLabels[item.status] ?? item.status}</span>
              </div>
            </Link>
          ))
        )}
      </section>
    </main>
  );
}
