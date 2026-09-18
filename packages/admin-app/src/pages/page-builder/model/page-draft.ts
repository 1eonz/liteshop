import type { StorePageSchema } from '@liteshop/shared-types';
import { PAGE_BUILDER_STORAGE_KEY } from './page-builder-model';

export type DraftSaveResult = 'saved' | 'unchanged' | 'failed';

/** 每页保留草稿，另存最新草稿用于下次打开；不把存储失败报告为成功。 */
export function writePageDraft(page: StorePageSchema, storage: Pick<Storage, 'getItem' | 'setItem'>): DraftSaveResult {
  try {
    const content = JSON.stringify(page);
    const pageKey = `${PAGE_BUILDER_STORAGE_KEY}:${page.channel ?? 'store'}:${page.id}`;
    if (storage.getItem(pageKey) === content && storage.getItem(PAGE_BUILDER_STORAGE_KEY) === content) return 'unchanged';
    storage.setItem(pageKey, content);
    storage.setItem(PAGE_BUILDER_STORAGE_KEY, content);
    return 'saved';
  } catch {
    return 'failed';
  }
}

/** 回调读取最新画布；普通渲染不会重置 30 秒保存周期。 */
export function startDraftAutoSave(readPage: () => StorePageSchema, onResult: (result: DraftSaveResult) => void): () => void {
  const timer = setInterval(() => {
    try { onResult(writePageDraft(readPage(), window.localStorage)); }
    catch { onResult('failed'); }
  }, 30_000);
  return () => clearInterval(timer);
}
