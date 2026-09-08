import type { ApiEnvelope, StorePageSchema } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取商城首页已发布 Schema。 */
export async function getStoreHomePage(): Promise<StorePageSchema> {
  const response = await httpClient.get<ApiEnvelope<StorePageSchema>>('/pages/1/schema');
  return response.data.data;
}
