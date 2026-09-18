import type { DashboardData } from '@liteshop/shared-types';
import { messages } from '../../../i18n/messages';

export interface DashboardMetric {
  label: string;
  value: string;
  trend: string;
}

/** 将看板领域数据转换为指标卡展示模型。 */
export function buildDashboardMetrics(
  data: DashboardData | undefined,
  formatAmount: (amountCents: number) => string,
): DashboardMetric[] {
  if (!data) return [];
  return [
    { label: messages.dashboard.sales, value: formatAmount(data.metrics.salesAmount), trend: messages.dashboard.paid },
    { label: messages.dashboard.orders, value: String(data.metrics.orderCount), trend: messages.dashboard.aggregate },
    { label: messages.dashboard.products, value: String(data.metrics.productCount), trend: messages.dashboard.productCount },
    {
      label: messages.dashboard.shipment,
      value: String(data.metrics.pendingShipmentCount),
      trend: data.metrics.pendingShipmentCount ? messages.dashboard.pending : messages.dashboard.clear,
    },
  ];
}
