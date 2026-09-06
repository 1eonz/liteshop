import { describe, expect, it } from 'vitest';
import { metricLabels } from './app-data';
import { buildDashboardMetrics } from './features/dashboard';

describe('后台看板指标', () => {
  it('包含四个指标卡标题', () => {
    expect(metricLabels).toHaveLength(4);
  });

  it('没有看板数据时不生成虚假指标', () => {
    expect(buildDashboardMetrics(undefined, (value) => String(value))).toEqual([]);
  });
});
