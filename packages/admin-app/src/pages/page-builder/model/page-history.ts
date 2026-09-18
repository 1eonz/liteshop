import type { StorePageSchema } from '@liteshop/shared-types';

export interface PageHistory {
  page: StorePageSchema;
  past: StorePageSchema[];
  future: StorePageSchema[];
}

export type PageHistoryAction =
  | { type: 'edit'; update: (page: StorePageSchema) => StorePageSchema }
  | { type: 'replace' | 'sync'; page: StorePageSchema }
  | { type: 'undo' | 'redo' };

/** 单一纯转换同时维护画布与两侧历史，React 重放不会产生额外副作用。 */
export function reducePageHistory(state: PageHistory, action: PageHistoryAction, limit = 50): PageHistory {
  switch (action.type) {
    case 'replace': return { page: action.page, past: [], future: [] };
    case 'sync': return { ...state, page: action.page };
    case 'edit': {
      const page = action.update(state.page);
      if (page === state.page) return state;
      return { page, past: [...state.past, state.page].slice(-limit), future: [] };
    }
    case 'undo': {
      const page = state.past.at(-1);
      return page ? { page, past: state.past.slice(0, -1), future: [state.page, ...state.future].slice(0, limit) } : state;
    }
    case 'redo': {
      const page = state.future[0];
      return page ? { page, past: [...state.past, state.page].slice(-limit), future: state.future.slice(1) } : state;
    }
  }
}
