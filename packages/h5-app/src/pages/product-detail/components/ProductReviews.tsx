import type { JSX } from 'react';
import type { ProductReviewResponse } from '@liteshop/shared-types';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

interface ProductReviewsProps {
  data: ProductReviewResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/** 商品评价区域，隔离评价列表的加载、错误和空状态。 */
export function ProductReviews({
  data,
  isLoading,
  isError,
  onRetry,
}: ProductReviewsProps): JSX.Element {
  return (
    <section className="detail-section" aria-label="商品评价">
      <div className="section-title">
        <h2>用户评价</h2>
        <span>{data?.averageRating ? `${data.averageRating} 分` : '暂无评分'}</span>
      </div>
      {isLoading && <FeedbackState>评价加载中…</FeedbackState>}
      {isError && <ErrorState onRetry={onRetry}>评价加载失败，请稍后重试。</ErrorState>}
      {!isLoading && !isError && !data?.items.length && <p className="muted">暂无已审核评价</p>}
      {data?.items.slice(0, 3).map((review) => (
        <article className="review-item" key={review.id}>
          <div aria-label={`${review.rating} 星评分`}>
            {'★'.repeat(review.rating)}
            {'☆'.repeat(5 - review.rating)}
          </div>
          <p>{review.content || '用户未填写文字评价'}</p>
          {review.merchantReply && (
            <p className="review-item__reply">
              <strong>商家回复：</strong>
              {review.merchantReply}
            </p>
          )}
          <time dateTime={review.createdAt}>
            {new Date(review.createdAt).toLocaleDateString('zh-CN')}
          </time>
        </article>
      ))}
    </section>
  );
}
