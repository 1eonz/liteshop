import type { JSX } from 'react';
import { useState } from 'react';
import {
  AfterSaleStatus,
  AfterSaleType,
  formatPrice,
  type AfterSaleRecord,
} from '@liteshop/shared-types';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useDebounceAction } from '../../hooks';
import { useAdminAfterSaleMutations, useAdminAfterSalesQuery } from '../../features/after-sales';

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

function statusClass(status: AfterSaleStatus): string {
  if (status === AfterSaleStatus.COMPLETED) return 'status-badge status-badge--on';
  if (status === AfterSaleStatus.REJECTED || status === AfterSaleStatus.CANCELLED) {
    return 'status-badge status-badge--danger';
  }
  return 'status-badge';
}

interface AfterSaleRowProps {
  item: AfterSaleRecord;
  onAudit: (item: AfterSaleRecord, approved: boolean) => void;
  onComplete: (item: AfterSaleRecord) => void;
  disabled: boolean;
}

function AfterSaleRow({ item, onAudit, onComplete, disabled }: AfterSaleRowProps): JSX.Element {
  const [expanded, setExpanded] = useState(false);
  return (
    <article className="after-sale-admin-row">
      <button
        className="after-sale-admin-row__summary"
        type="button"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        <span>
          <strong>{item.afterSaleNo}</strong>
          <small>
            {typeLabels[item.type]} · 订单项 #{item.orderItemId}
          </small>
        </span>
        <span>
          <strong>{formatPrice(item.amountCents)}</strong>
          <em className={statusClass(item.status)}>{statusLabels[item.status]}</em>
        </span>
      </button>
      {expanded && (
        <div className="after-sale-admin-row__detail">
          <p>{item.reason}</p>
          <p className="muted">申请时间：{new Date(item.createdAt).toLocaleString('zh-CN')}</p>
          {item.returnTrackingNo && <p>退货物流：{item.returnTrackingNo}</p>}
          {item.auditReason && <p>审核备注：{item.auditReason}</p>}
          <div className="row-actions">
            {item.status === AfterSaleStatus.PENDING_REVIEW && (
              <>
                <button type="button" disabled={disabled} onClick={() => onAudit(item, true)}>
                  同意申请
                </button>
                <button
                  className="danger-button"
                  type="button"
                  disabled={disabled}
                  onClick={() => onAudit(item, false)}
                >
                  拒绝申请
                </button>
              </>
            )}
            {(item.status === AfterSaleStatus.RETURNED ||
              item.status === AfterSaleStatus.REFUNDING) && (
              <button type="button" disabled={disabled} onClick={() => onComplete(item)}>
                确认完成
              </button>
            )}
          </div>
        </div>
      )}
    </article>
  );
}

/** 后台售后审核工作区，审核和完成动作都进入服务端审计日志。 */
export function AfterSalesPage(): JSX.Element {
  const [status, setStatus] = useState<AfterSaleStatus | undefined>();
  const [feedback, setFeedback] = useState('');
  const query = useAdminAfterSalesQuery(status);
  const mutations = useAdminAfterSaleMutations();
  const audit = async (item: AfterSaleRecord, approved: boolean): Promise<void> => {
    const reason = window.prompt(approved ? '审核备注（可选）' : '请输入拒绝原因') ?? '';
    if (!approved && !reason.trim()) return;
    setFeedback('');
    try {
      await mutations.audit.mutateAsync({ afterSaleId: item.id, approved, reason: reason.trim() });
      setFeedback(approved ? '已同意售后申请。' : '已拒绝售后申请。');
    } catch {
      setFeedback('审核失败，请确认权限和售后状态后重试。');
    }
  };
  const complete = async (item: AfterSaleRecord): Promise<void> => {
    setFeedback('');
    try {
      await mutations.complete.mutateAsync(item.id);
      setFeedback('售后已完成，退款或换货入库已处理。');
    } catch {
      setFeedback('完成售后失败，请确认支付和库存状态后重试。');
    }
  };
  const [runAudit, auditing] = useDebounceAction(audit, 500);
  const [runComplete, completing] = useDebounceAction(complete, 500);
  const busy = auditing || completing || mutations.audit.isPending || mutations.complete.isPending;

  if (query.isLoading) return <FeedbackState>售后列表加载中…</FeedbackState>;
  if (query.isError) {
    return (
      <ErrorState onRetry={() => void query.refetch()}>
        售后列表加载失败，请检查权限后重试。
      </ErrorState>
    );
  }
  const items = query.data ?? [];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>售后与退款</p>
          <h1>售后审核</h1>
        </div>
        <label>
          状态筛选
          <select
            value={status ?? ''}
            onChange={(event) =>
              setStatus((event.target.value || undefined) as AfterSaleStatus | undefined)
            }
          >
            <option value="">全部</option>
            {Object.values(AfterSaleStatus).map((value) => (
              <option value={value} key={value}>
                {statusLabels[value]}
              </option>
            ))}
          </select>
        </label>
      </header>
      {feedback && <FeedbackState>{feedback}</FeedbackState>}
      <section className="editor-form after-sale-admin-list" aria-label="售后审核列表">
        {items.length === 0 ? (
          <EmptyState title="暂无售后单" description="新的售后申请会出现在这里。" />
        ) : (
          items.map((item) => (
            <AfterSaleRow
              key={item.id}
              item={item}
              onAudit={(record, approved) => void runAudit(record, approved)}
              onComplete={(record) => void runComplete(record)}
              disabled={busy}
            />
          ))
        )}
      </section>
    </div>
  );
}
