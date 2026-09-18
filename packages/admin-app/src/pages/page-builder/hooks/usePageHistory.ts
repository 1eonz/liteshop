import { useCallback, useRef, useReducer } from 'react';
import type { StorePageSchema } from '@liteshop/shared-types';
import { reducePageHistory } from '../model/page-history';
import type { PageHistory, PageHistoryAction } from '../model/page-history';

/** 管理搭建器页面状态及有限步历史，避免页面组件承担撤销重做细节。 */
export function usePageHistory(
  initialPage: () => StorePageSchema,
  maxHistory: number,
 ) {
  const [state, dispatch] = useReducer(
    (current: PageHistory, action: PageHistoryAction) => reducePageHistory(current, action, maxHistory),
    undefined,
    () => ({ page: initialPage(), past: [], future: [] }),
  );
  const { page, past: history, future } = state;
  const pageRef = useRef(page);
  pageRef.current = page;

  const updatePage = useCallback(
    (updater: (current: StorePageSchema) => StorePageSchema): void => {
      dispatch({ type: 'edit', update: updater });
    },
    [],
  );

  const undo = useCallback((): void => {
    dispatch({ type: 'undo' });
  }, []);

  const redo = useCallback((): void => {
    dispatch({ type: 'redo' });
  }, []);
  const replacePage = useCallback((next: StorePageSchema) => dispatch({ type: 'replace', page: next }), []);
  const syncPage = useCallback((next: StorePageSchema) => dispatch({ type: 'sync', page: next }), []);

  return { page, replacePage, syncPage, pageRef, history, future, updatePage, undo, redo };
}
