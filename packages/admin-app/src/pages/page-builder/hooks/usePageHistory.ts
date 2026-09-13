import { useCallback, useRef, useState } from 'react';
import type { Dispatch, MutableRefObject, SetStateAction } from 'react';
import type { StorePageSchema } from '@liteshop/shared-types';

interface UsePageHistoryResult {
  page: StorePageSchema;
  setPage: Dispatch<SetStateAction<StorePageSchema>>;
  pageRef: MutableRefObject<StorePageSchema>;
  history: StorePageSchema[];
  future: StorePageSchema[];
  updatePage: (updater: (current: StorePageSchema) => StorePageSchema) => void;
  undo: () => void;
  redo: () => void;
}

/** 管理搭建器页面状态及有限步历史，避免页面组件承担撤销重做细节。 */
export function usePageHistory(
  initialPage: () => StorePageSchema,
  maxHistory: number,
  onNotice: (message: string) => void,
): UsePageHistoryResult {
  const [page, setPage] = useState<StorePageSchema>(initialPage);
  const [history, setHistory] = useState<StorePageSchema[]>([]);
  const [future, setFuture] = useState<StorePageSchema[]>([]);
  const pageRef = useRef(page);
  pageRef.current = page;

  const updatePage = useCallback(
    (updater: (current: StorePageSchema) => StorePageSchema): void => {
      setPage((current) => {
        const next = updater(current);
        setHistory((items) => [...items, current].slice(-maxHistory));
        setFuture([]);
        return next;
      });
      onNotice('未保存更改');
    },
    [maxHistory, onNotice],
  );

  const undo = useCallback((): void => {
    setHistory((items) => {
      const previous = items.at(-1);
      if (!previous) return items;
      setFuture((itemsFuture) => [pageRef.current, ...itemsFuture].slice(0, maxHistory));
      setPage(previous);
      onNotice('已撤销');
      return items.slice(0, -1);
    });
  }, [maxHistory, onNotice]);

  const redo = useCallback((): void => {
    setFuture((items) => {
      const next = items[0];
      if (!next) return items;
      setHistory((itemsHistory) => [...itemsHistory, pageRef.current].slice(-maxHistory));
      setPage(next);
      onNotice('已重做');
      return items.slice(1);
    });
  }, [maxHistory, onNotice]);

  return { page, setPage, pageRef, history, future, updatePage, undo, redo };
}
