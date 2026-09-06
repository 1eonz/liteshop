'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

type Action<T extends unknown[]> = (...args: T) => void | Promise<void>;
type TimerHandle = ReturnType<typeof globalThis.setTimeout>;

export interface DebounceControllerOptions {
  /** 获取每次执行后的冷却时长，单位为毫秒。 */
  getDelay?: () => number;
  /** 控制器状态变化时调用，卸载后不会再调用。 */
  onStateChange?: (running: boolean) => void;
}

export interface DebounceController<T extends unknown[]> {
  /** 执行动作；执行中和冷却期间的调用会被忽略。 */
  run: (...args: T) => Promise<void>;
  /** 释放控制器并取消尚未完成的冷却定时器。 */
  dispose: () => void;
  /** 返回动作是否仍处于执行或冷却阶段。 */
  isRunning: () => boolean;
}

/**
 * 创建可卸载的防抖动作控制器。
 *
 * 动作本身立即执行，动作完成后进入冷却期；动作异常会原样抛出，
 * 但控制器仍会在冷却期结束后释放并允许后续调用。
 */
export function createDebouncedAction<T extends unknown[]>(
  action: Action<T>,
  options: DebounceControllerOptions = {},
): DebounceController<T> {
  const getDelay = options.getDelay ?? (() => 500);
  const onStateChange = options.onStateChange ?? (() => undefined);
  let running = false;
  let disposed = false;
  let timer: TimerHandle | null = null;
  let resolveCooldown: (() => void) | null = null;

  const setRunning = (value: boolean): void => {
    running = value;
    if (!disposed) onStateChange(value);
  };

  const waitForCooldown = (milliseconds: number): Promise<void> => {
    if (disposed || milliseconds <= 0) return Promise.resolve();
    return new Promise<void>((resolve) => {
      resolveCooldown = () => {
        timer = null;
        resolveCooldown = null;
        resolve();
      };
      timer = globalThis.setTimeout(resolveCooldown, milliseconds);
    });
  };

  const run = async (...args: T): Promise<void> => {
    if (disposed || running) return;
    setRunning(true);
    try {
      await action(...args);
    } finally {
      if (!disposed) await waitForCooldown(Math.max(0, getDelay()));
      setRunning(false);
    }
  };

  const dispose = (): void => {
    if (disposed) return;
    disposed = true;
    if (timer !== null) {
      globalThis.clearTimeout(timer);
      timer = null;
    }
    resolveCooldown?.();
    resolveCooldown = null;
    running = false;
  };

  return { run, dispose, isRunning: () => running };
}

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
  const actionRef = useRef(action);
  const delayRef = useRef(delay);
  const controllerRef = useRef<DebounceController<T> | null>(null);
  const mountedRef = useRef(true);

  actionRef.current = action;
  delayRef.current = delay;

  if (controllerRef.current === null) {
    controllerRef.current = createDebouncedAction((...args: T) => actionRef.current(...args), {
      getDelay: () => delayRef.current,
      onStateChange: (running) => {
        if (mountedRef.current) setLoading(running);
      },
    });
  }

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      controllerRef.current?.dispose();
    };
  }, []);

  const run = useCallback((...args: T): Promise<void> => {
    return controllerRef.current?.run(...args) ?? Promise.resolve();
  }, []);

  return [run, loading];
}
