import { useCallback, useRef, useState, type TouchEventHandler } from 'react';

interface UsePullToRefreshOptions {
  onRefresh: () => Promise<unknown> | unknown;
  threshold?: number;
  disabled?: boolean;
}

export interface PullToRefreshResult {
  handlers: {
    onTouchStart: TouchEventHandler<HTMLElement>;
    onTouchMove: TouchEventHandler<HTMLElement>;
    onTouchEnd: TouchEventHandler<HTMLElement>;
    onTouchCancel: TouchEventHandler<HTMLElement>;
  };
  pullDistance: number;
  isRefreshing: boolean;
  threshold: number;
}

/**
 * H5 首页下拉刷新控制器，只在页面滚动到顶部时接管触摸手势。
 * 刷新动作由调用方提供，Hook 不直接依赖 React Query，便于在预览页复用。
 */
export function usePullToRefresh({
  onRefresh,
  threshold = 72,
  disabled = false,
}: UsePullToRefreshOptions): PullToRefreshResult {
  const startY = useRef<number | null>(null);
  const tracking = useRef(false);
  const pullDistanceRef = useRef(0);
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const reset = useCallback((): void => {
    startY.current = null;
    tracking.current = false;
    pullDistanceRef.current = 0;
    setPullDistance(0);
  }, []);

  const onTouchStart: TouchEventHandler<HTMLElement> = useCallback(
    (event) => {
      if (disabled || isRefreshing || event.touches.length !== 1 || window.scrollY > 0) {
        return;
      }
      startY.current = event.touches[0]?.clientY ?? null;
      tracking.current = startY.current !== null;
    },
    [disabled, isRefreshing],
  );

  const onTouchMove: TouchEventHandler<HTMLElement> = useCallback(
    (event) => {
      if (!tracking.current || startY.current === null || disabled || isRefreshing) return;
      const currentY = event.touches[0]?.clientY ?? startY.current;
      const distance = Math.max(0, Math.min(threshold * 1.5, currentY - startY.current));
      if (distance > 0) event.preventDefault();
      pullDistanceRef.current = distance;
      setPullDistance(distance);
    },
    [disabled, isRefreshing, threshold],
  );

  const finish = useCallback(async (): Promise<void> => {
    const shouldRefresh = pullDistanceRef.current >= threshold && !disabled && !isRefreshing;
    reset();
    if (!shouldRefresh) return;
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  }, [disabled, isRefreshing, onRefresh, reset, threshold]);

  const onTouchEnd: TouchEventHandler<HTMLElement> = useCallback(() => {
    void finish();
  }, [finish]);

  const onTouchCancel: TouchEventHandler<HTMLElement> = useCallback(() => {
    reset();
  }, [reset]);

  return {
    handlers: { onTouchStart, onTouchMove, onTouchEnd, onTouchCancel },
    pullDistance,
    isRefreshing,
    threshold,
  };
}
