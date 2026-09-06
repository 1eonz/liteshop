import type { ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface NotificationItem {
  id: number;
  type: string;
  title: string;
  content: string;
  readAt: string | null;
  createdAt: string;
}

export interface NotificationResponse {
  items: NotificationItem[];
  unreadCount: number;
}

/** 读取当前用户站内通知。 */
export async function listNotifications(): Promise<NotificationResponse> {
  const response = await httpClient.get<ApiEnvelope<NotificationResponse>>('/notifications');
  return response.data.data;
}

/** 标记单条通知已读。 */
export async function markNotificationRead(notificationId: number): Promise<void> {
  await httpClient.put<ApiEnvelope<unknown>>(`/notifications/${notificationId}/read`);
}

/** 标记全部通知已读。 */
export async function markAllNotificationsRead(): Promise<void> {
  await httpClient.put<ApiEnvelope<unknown>>('/notifications/read-all');
}
