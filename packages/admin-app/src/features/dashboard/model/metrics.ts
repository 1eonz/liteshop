import type { DashboardData } from '@liteshop/shared-types';

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
    { label: '今日销售额', value: formatAmount(data.metrics.salesAmount), trend: '实时聚合' },
    { label: '支付订单', value: String(data.metrics.orderCount), trend: '累计订单' },
    { label: '在售商品', value: String(data.metrics.productCount), trend: '商品总量' },
    {
      label: '待发货',
      value: String(data.metrics.pendingShipmentCount),
      trend: data.metrics.pendingShipmentCount ? '需处理' : '已清空',
    },
  ];
}
