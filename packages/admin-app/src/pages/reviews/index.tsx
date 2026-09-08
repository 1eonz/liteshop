import type { JSX } from 'react';
import { useState } from 'react';
import { EmptyState, ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useDebounceAction } from '../../hooks';
import {
  useAdminReviewMutation,
  useAdminReviewReplyMutation,
  useAdminReviewsQuery,
} from '../../features/reviews';
import type { AdminReviewRecord } from '@liteshop/shared-types';

/** 后台评价审核页面，审核动作进入统一审计和幂等链路。 */
export function ReviewsPage(): JSX.Element {
  const query = useAdminReviewsQuery();
  const mutation = useAdminReviewMutation();
  const replyMutation = useAdminReviewReplyMutation();
  const [selected, setSelected] = useState<AdminReviewRecord | null>(null);
  const [feedback, setFeedback] = useState('');
  const [reply, setReply] = useState('');
  const audit = async (status: 'APPROVED' | 'REJECTED'): Promise<void> => {
    if (!selected) return;
    const reason = status === 'REJECTED' ? (window.prompt('请输入拒绝原因') ?? '') : '';
    if (status === 'REJECTED' && !reason.trim()) return;
    try {
      await mutation.mutateAsync({ reviewId: selected.id, status, reason: reason.trim() });
      setSelected(null);
      setFeedback(status === 'APPROVED' ? '评价已通过。' : '评价已拒绝。');
    } catch {
      setFeedback('审核失败，请确认权限和评价状态后重试。');
    }
  };
  const saveReply = async (): Promise<void> => {
    if (!selected || selected.status !== 'APPROVED' || !reply.trim()) return;
    try {
      await replyMutation.mutateAsync({ reviewId: selected.id, reply: reply.trim() });
      setReply('');
      setFeedback('商家回复已保存。');
    } catch {
      setFeedback('商家回复保存失败，请稍后重试。');
    }
  };
  const [runAudit, auditing] = useDebounceAction(audit, 500);
  const [runReply, replying] = useDebounceAction(saveReply, 800);
  if (query.isLoading) return <FeedbackState>评价列表加载中…</FeedbackState>;
  if (query.isError)
    return <ErrorState onRetry={() => void query.refetch()}>评价列表加载失败，请重试。</ErrorState>;
  const items = query.data ?? [];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>内容审核</p>
          <h1>商品评价</h1>
        </div>
      </header>
      {feedback && (
        <p className="feedback" role="status">
          {feedback}
        </p>
      )}
      <section className="editor-form product-list" aria-label="评价列表">
        {!items.length ? (
          <EmptyState title="暂无待审核评价" description="新提交的评价会显示在这里。" />
        ) : (
          items.map((item) => (
            <button
              className="admin-product-row"
              type="button"
              key={item.id}
              onClick={() => setSelected(item)}
            >
              <span>
                <strong>
                  {'★'.repeat(item.rating)}
                  {'☆'.repeat(5 - item.rating)}
                </strong>
                <small>{item.content || '用户未填写文字评价'}</small>
              </span>
              <span>{item.status}</span>
              <time dateTime={item.createdAt}>
                {new Date(item.createdAt).toLocaleDateString('zh-CN')}
              </time>
            </button>
          ))
        )}
      </section>
      {selected && (
        <section className="panel" aria-label="评价详情">
          <div className="panel-title">
            <h2>评价详情</h2>
            <button className="ghost-button" type="button" onClick={() => setSelected(null)}>
              关闭
            </button>
          </div>
          <p>{selected.content || '用户未填写文字评价'}</p>
          <p className="muted">
            商品 #{selected.productId} · 用户 #{selected.userId}
          </p>
          {selected.status === 'APPROVED' && (
            <label className="reply-field">
              商家回复
              <textarea
                value={reply}
                maxLength={2000}
                placeholder={selected.merchantReply ?? '回复会展示在商品评价中'}
                onChange={(event) => setReply(event.target.value)}
              />
            </label>
          )}
          <div className="row-actions">
            <button
              type="button"
              disabled={auditing || mutation.isPending}
              onClick={() => void runAudit('APPROVED')}
            >
              通过
            </button>
            <button
              className="danger-button"
              type="button"
              disabled={auditing || mutation.isPending}
              onClick={() => void runAudit('REJECTED')}
            >
              拒绝
            </button>
            {selected.status === 'APPROVED' && (
              <button
                type="button"
                disabled={replying || replyMutation.isPending || !reply.trim()}
                onClick={() => void runReply()}
              >
                {replying ? '保存中…' : '保存回复'}
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
