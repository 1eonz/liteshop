import { useCallback, useEffect, useRef, useState } from 'react';

type Action<T extends unknown[]> = (...args: T) => void | Promise<void>;

/**
 * 写操作防抖 Hook：动作立即执行，执行和冷却期间锁定调用。
 *
 * 该 Hook 只负责并发保护和按钮状态，业务错误仍由调用方处理。
 */
export function useDebounceAction<T extends unknown[]>(
  action: Action<T>,
  delay = 500,
): [(...args: T) => Promise<void>, boolean] {
  const [loading, setLoading] = useState(false);
  const runningRef = useRef(false);
  const mountedRef = useRef(true);

  useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const run = useCallback(
    async (...args: T): Promise<void> => {
      if (runningRef.current) return;
      runningRef.current = true;
      if (mountedRef.current) setLoading(true);
      try {
        await action(...args);
      } finally {
        await new Promise<void>((resolve) => {
          globalThis.setTimeout(resolve, Math.max(0, delay));
        });
        runningRef.current = false;
        if (mountedRef.current) setLoading(false);
      }
    },
    [action, delay],
  );

  return [run, loading];
}
