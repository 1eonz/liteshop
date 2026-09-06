import type { JSX } from 'react';
import { useMemo } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from '../../service/notifications';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useSessionStore } from '../../store/session';

/** 站内通知页面，提供未读状态和已读操作。 */
export function NotificationsPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const queryClient = useQueryClient();
  const notificationQuery = useQuery({
    queryKey: ['notifications'],
    enabled: authenticated,
    queryFn: listNotifications,
  });
  const readMutation = useMutation({
    mutationFn: markNotificationRead,
    retry: 0,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });
  const readAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    retry: 0,
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });
  const [readAll, readingAll] = useDebounceAction(() => readAllMutation.mutateAsync(), 500);
  const [readOne, readingOne] = useDebounceAction(
    (notificationId: number) => readMutation.mutateAsync(notificationId),
    500,
  );
  const unreadCount = useMemo(
    () => notificationQuery.data?.unreadCount ?? 0,
    [notificationQuery.data],
  );
  if (!authenticated) return <Navigate to="/login" state={{ from: '/notifications' }} replace />;
  if (notificationQuery.isLoading) {
    return (
      <main className="trade-page">
        <FeedbackState>通知加载中…</FeedbackState>
      </main>
    );
  }
  if (notificationQuery.isError) {
    return (
      <main className="trade-page">
        <ErrorState onRetry={() => void notificationQuery.refetch()}>
          通知加载失败，请重试。
        </ErrorState>
      </main>
    );
  }
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回
        </Link>
        <h1>通知中心</h1>
        <button
          className="text-action"
          type="button"
          disabled={!unreadCount || readingAll}
          onClick={() => void readAll()}
        >
          全部已读
        </button>
      </header>
      {notificationQuery.data?.items.length ? (
        notificationQuery.data.items.map((notification) => (
          <article
            className={`notification-item${notification.readAt ? '' : ' notification-item--unread'}`}
            key={notification.id}
          >
            <div>
              <h2>{notification.title}</h2>
              <p>{notification.content}</p>
              <time dateTime={notification.createdAt}>
                {new Date(notification.createdAt).toLocaleString('zh-CN')}
              </time>
            </div>
            {!notification.readAt && (
              <button
                className="text-action"
                type="button"
                disabled={readMutation.isPending || readingOne}
                onClick={() => void readOne(notification.id)}
              >
                标记已读
              </button>
            )}
          </article>
        ))
      ) : (
        <p className="feedback">暂无通知</p>
      )}
    </main>
  );
}
