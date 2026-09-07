import type { ContactFormStatus } from '@liteshop/shared-types';
import type { JSX } from 'react';
import { useState } from 'react';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useDebounceAction } from '../../hooks';
import { useContactSubmissionMutations, useContactSubmissionsQuery } from '../../features/contact';

const STATUS_LABELS: Record<ContactFormStatus, string> = {
  NEW: '待处理',
  IN_PROGRESS: '跟进中',
  RESOLVED: '已解决',
  SPAM: '垃圾信息',
};

/** 官网联系表单跟进工作区。 */
export function ContactPage(): JSX.Element {
  const [statusFilter, setStatusFilter] = useState<ContactFormStatus | undefined>();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const query = useContactSubmissionsQuery(statusFilter);
  const mutation = useContactSubmissionMutations();
  const selected = query.data?.find((item) => item.id === selectedId) ?? null;
  const updateStatus = async (status: ContactFormStatus): Promise<void> => {
    if (!selected) return;
    await mutation.mutateAsync({ submissionId: selected.id, status });
    setSelectedId(null);
  };
  const [runUpdateStatus, updating] = useDebounceAction(updateStatus, 500);

  if (query.isLoading) return <FeedbackState>联系表单加载中…</FeedbackState>;
  if (query.isError) {
    return (
      <ErrorState onRetry={() => void query.refetch()}>
        联系表单加载失败，请检查权限后重试。
      </ErrorState>
    );
  }
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>官网运营</p>
          <h1>联系表单</h1>
        </div>
        <label>
          状态筛选
          <select
            value={statusFilter ?? ''}
            onChange={(event) =>
              setStatusFilter((event.target.value || undefined) as ContactFormStatus | undefined)
            }
          >
            <option value="">全部</option>
            {Object.entries(STATUS_LABELS).map(([value, label]) => (
              <option value={value} key={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
      </header>
      <section className="editor-form product-list" aria-label="联系表单列表">
        {query.data?.length ? (
          query.data.map((item) => (
            <button
              className="admin-product-row"
              type="button"
              key={item.id}
              onClick={() => setSelectedId(item.id)}
            >
              <span>
                <strong>{item.name}</strong>
                <small>
                  {item.email}
                  {item.company ? ` · ${item.company}` : ''}
                </small>
              </span>
              <span>{STATUS_LABELS[item.status]}</span>
              <time dateTime={item.createdAt}>
                {new Date(item.createdAt).toLocaleDateString('zh-CN')}
              </time>
            </button>
          ))
        ) : (
          <div className="feedback">暂无联系表单。</div>
        )}
      </section>
      {selected && (
        <section className="panel" aria-label="联系表单详情">
          <div className="panel-title">
            <h2>{selected.name} 的留言</h2>
            <button className="ghost-button" type="button" onClick={() => setSelectedId(null)}>
              关闭
            </button>
          </div>
          <p className="muted">
            {selected.email}
            {selected.phone ? ` · ${selected.phone}` : ''}
          </p>
          <p className="contact-message">{selected.message}</p>
          <div className="builder-toolbar__actions" aria-label="更新联系表单状态">
            {(Object.keys(STATUS_LABELS) as ContactFormStatus[]).map((status) => (
              <button
                key={status}
                type="button"
                disabled={updating || mutation.isPending || status === selected.status}
                onClick={() => void runUpdateStatus(status)}
              >
                {STATUS_LABELS[status]}
              </button>
            ))}
          </div>
          {mutation.isError && (
            <p className="feedback error-state" role="alert">
              状态更新失败，请重试。
            </p>
          )}
        </section>
      )}
    </div>
  );
}
