import type { JSX } from 'react';
import type { CSSProperties } from 'react';
import { EmptyState, ErrorState } from '@liteshop/shared-components';
import { SchemaRenderer } from '../../components/SchemaRenderer';
import { useStoreHomePageQuery } from '../../features/catalog';
import { usePullToRefresh } from '../../hooks/usePullToRefresh';
import { HomeSkeleton } from './HomeSkeleton';

/** H5 首页只负责页面状态编排，具体板块全部由已发布 Schema 渲染。 */
export function HomePage(): JSX.Element {
  const storePageQuery = useStoreHomePageQuery();
  const pullToRefresh = usePullToRefresh({
    onRefresh: () => storePageQuery.refetch(),
    disabled: storePageQuery.isLoading,
  });
  const refreshStyle = {
    '--pull-refresh-distance': `${pullToRefresh.pullDistance}px`,
  } as CSSProperties;

  if (storePageQuery.isLoading) {
    return (
      <main className="h5-shell" {...pullToRefresh.handlers}>
        <HomeSkeleton />
      </main>
    );
  }

  if (storePageQuery.isError) {
    return (
      <main className="h5-shell" {...pullToRefresh.handlers}>
        <ErrorState onRetry={() => void storePageQuery.refetch()}>
          首页配置加载失败，请稍后重试
        </ErrorState>
      </main>
    );
  }

  const schema = storePageQuery.data;
  if (!schema || schema.components.length === 0) {
    return (
      <main className="h5-shell" {...pullToRefresh.handlers}>
        <EmptyState title="首页暂未配置" description="请在后台搭建器发布商城首页内容。" />
      </main>
    );
  }

  return (
    <main className="h5-shell" style={refreshStyle} {...pullToRefresh.handlers}>
      {pullToRefresh.pullDistance > 0 || pullToRefresh.isRefreshing ? (
        <div className="pull-refresh-indicator" role="status" aria-live="polite">
          {pullToRefresh.isRefreshing
            ? '正在刷新首页…'
            : pullToRefresh.pullDistance >= pullToRefresh.threshold
              ? '松开刷新首页'
              : '下拉刷新首页'}
        </div>
      ) : null}
      <SchemaRenderer schema={schema} />
    </main>
  );
}
