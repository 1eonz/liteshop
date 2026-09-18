import { useEffect } from 'react';
import type { MutableRefObject } from 'react';
import type { StorePageSchema } from '@liteshop/shared-types';
import { startDraftAutoSave } from '../model/page-draft';
import { messages } from '../../../i18n/messages';

/** 定时将当前 Schema 写入本地草稿，接口保存仍由页面显式触发。 */
export function useAutoSave(
  pageRef: MutableRefObject<StorePageSchema>,
  onNotice: (message: string) => void,
): void {
  useEffect(() => {
    return startDraftAutoSave(() => pageRef.current, (result) => {
      if (result !== 'unchanged') onNotice(result === 'saved' ? messages.builder.autoSaved : messages.builder.draftFailed);
    });
  }, [onNotice, pageRef]);
}
