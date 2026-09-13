import { useEffect } from 'react';
import type { MutableRefObject } from 'react';
import type { StorePageSchema } from '@liteshop/shared-types';

/** 定时将当前 Schema 写入本地草稿，接口保存仍由页面显式触发。 */
export function useAutoSave(
  pageRef: MutableRefObject<StorePageSchema>,
  storageKey: string,
  onSaved: () => void,
): void {
  useEffect(() => {
    const timer = window.setInterval(() => {
      window.localStorage.setItem(storageKey, JSON.stringify(pageRef.current));
      onSaved();
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [onSaved, pageRef, storageKey]);
}
