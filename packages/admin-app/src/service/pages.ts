import type { ApiEnvelope, StorePageSchema } from '@liteshop/shared-types';
import { httpClient } from './http';

export interface ManagedPageSummary {
  id: number;
  slug: string;
  name: string;
  version: number;
  isHome: boolean;
  updatedAt?: string;
}

/** 读取页面管理列表。 */
export async function listManagedPages(): Promise<ManagedPageSummary[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: ManagedPageSummary[] }>>('/pages');
  return response.data.data.items;
}

/** 保存页面 Schema，后端负责版本递增和幂等。 */
export async function saveManagedPage(page: StorePageSchema): Promise<StorePageSchema> {
  const response = await httpClient.put<ApiEnvelope<StorePageSchema>>(
    `/pages/${page.id}/schema`,
    page,
  );
  return response.data.data;
}

/** 复制页面并生成新路由。 */
export async function copyManagedPage(
  pageId: number,
  input: { slug: string; name: string },
): Promise<StorePageSchema> {
  const response = await httpClient.post<ApiEnvelope<StorePageSchema>>(
    `/pages/${pageId}/copy`,
    input,
  );
  return response.data.data;
}

/** 设置首页。 */
export async function setManagedHome(pageId: number): Promise<StorePageSchema> {
  const response = await httpClient.put<ApiEnvelope<StorePageSchema>>(`/pages/${pageId}/home`);
  return response.data.data;
}
