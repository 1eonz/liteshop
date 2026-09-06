import type { JSX } from 'react';
import { lazy, Suspense, useCallback } from 'react';
import { useDashboardQuery } from '../../features/dashboard';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { formatPrice } from '../../utils/format-price';
import { buildDashboardMetrics } from '../../features/dashboard';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

const SalesTrendChart = lazy(async () => {
  const module = await import('../../components/SalesTrendChart');
  return { default: module.SalesTrendChart };
});

/** 后台数据看板页面，负责组合指标、趋势和排行视图。 */
export function DashboardPage(): JSX.Element {
  const query = useDashboardQuery();
  const data = query.data;
  const exportReport = useCallback(async () => {
    if (!data) return;
    const rows = [
      ['日期', '销售额（分）', '订单量'],
      ...data.trend.map((point) => [
        point.date,
        String(point.amount),
        String(point.orderCount ?? 0),
      ]),
    ];
    const csv = rows
      .map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(','))
      .join('\n');
    const url = URL.createObjectURL(new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = 'liteshop-sales-report.csv';
    link.click();
    URL.revokeObjectURL(url);
  }, [data]);
  const [download, downloading] = useDebounceAction(exportReport, 300);
  const metrics = buildDashboardMetrics(data, formatPrice);
  return (
    <div className="admin-dashboard">
      <header>
        <div>
          <p>运营中心</p>
          <h1>数据看板</h1>
        </div>
        <button
          className="secondary-button"
          type="button"
          disabled={!data || downloading}
          onClick={() => void download()}
        >
          {downloading ? '导出中…' : '导出报表'}
        </button>
      </header>
      {query.isLoading ? (
        <FeedbackState>看板数据加载中…</FeedbackState>
      ) : query.isError ? (
        <ErrorState onRetry={() => void query.refetch()}>看板数据加载失败，请刷新重试。</ErrorState>
      ) : (
        <>
          <div className="metrics">
            {metrics.map((metric) => (
              <article key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <em>{metric.trend}</em>
              </article>
            ))}
          </div>
          <section className="panel">
            <div className="panel-title">
              <h2>销售趋势</h2>
              <span>近 7 天</span>
            </div>
            <Suspense fallback={<div className="chart-loading">图表加载中…</div>}>
              <SalesTrendChart points={data?.trend ?? []} />
            </Suspense>
          </section>
          <section className="panel">
            <div className="panel-title">
              <h2>商品排行</h2>
              <span>按销量</span>
            </div>
            {(data?.ranking ?? []).length ? (
              data?.ranking.map((item, index) => (
                <div className="rank" key={item.name}>
                  <b>{index + 1}</b>
                  <span>{item.name}</span>
                  <strong>{item.salesCount} 件</strong>
                </div>
              ))
            ) : (
              <div className="feedback">暂无排行数据</div>
            )}
          </section>
          {data?.todo && (
            <section className="panel todo-panel">
              <div className="panel-title">
                <h2>待办提醒</h2>
                <span>需要关注</span>
              </div>
              <div className="todo-grid">
                <div>
                  <strong>{data.todo.pendingShipments}</strong>
                  <span>待发货订单</span>
                </div>
                <div>
                  <strong>{data.todo.lowStockSkus}</strong>
                  <span>低库存 SKU</span>
                </div>
                <div>
                  <strong>{data.todo.auditItems}</strong>
                  <span>待审计事项</span>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}
