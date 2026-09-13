import { describe, expect, it } from 'vitest';
import { metricLabels } from './app-data';
import { buildDashboardMetrics } from './features/dashboard';
import {
  COMPONENT_GROUPS,
  DEFAULT_PAGE,
  DEFAULT_SITE_PAGE,
  PAGE_TEMPLATES,
  SITE_COMPONENT_GROUPS,
  componentLabel,
  previewCopy,
} from './pages/page-builder/model/page-builder-model';

describe('后台看板指标', () => {
  it('包含四个指标卡标题', () => {
    expect(metricLabels).toHaveLength(4);
  });

  it('没有看板数据时不生成虚假指标', () => {
    expect(buildDashboardMetrics(undefined, (value) => String(value))).toEqual([]);
  });

  it('搭建器按渠道提供互斥的组件分组和默认画布', () => {
    expect(COMPONENT_GROUPS.flatMap((group) => group.types)).toContain('ProductGrid');
    expect(SITE_COMPONENT_GROUPS.flatMap((group) => group.types)).toContain('HeroSplit');
    expect(DEFAULT_PAGE.channel).toBe('store');
    expect(DEFAULT_SITE_PAGE.channel).toBe('site');
    expect(DEFAULT_PAGE.components).not.toEqual(DEFAULT_SITE_PAGE.components);
  });

  it('搭建器模板和预览摘要使用统一 Schema 模型', () => {
    expect(PAGE_TEMPLATES.length).toBeGreaterThanOrEqual(3);
    const component = { ...DEFAULT_PAGE.components[0], props: { title: '自定义区块' } };
    expect(componentLabel(component.type)).toBe('搜索框');
    expect(previewCopy(component)).toBe('自定义区块');
  });
});
