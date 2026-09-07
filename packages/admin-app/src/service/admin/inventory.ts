import type {
  ApiEnvelope,
  FreightTemplate,
  InventoryLedgerEntry,
  InventoryRow,
  PageResponse,
} from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 库存台账分页列表。 */
export async function listInventory(page = 1, pageSize = 50): Promise<PageResponse<InventoryRow>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<InventoryRow>>>(
    '/admin/inventory',
    { params: { page, pageSize } },
  );
  return response.data.data;
}

/** 手工调整库存，quantity 为整数件数。 */
export async function adjustInventory(
  skuId: number,
  quantity: number,
  reason: string,
): Promise<InventoryRow> {
  const response = await httpClient.post<ApiEnvelope<InventoryRow>>(
    `/admin/inventory/${skuId}/adjust`,
    { quantity, reason },
  );
  return response.data.data;
}

/** 读取指定 SKU 的库存流水。 */
export async function listInventoryLedger(skuId: number): Promise<InventoryLedgerEntry[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: InventoryLedgerEntry[] }>>(
    `/admin/inventory/${skuId}/ledger`,
  );
  return response.data.data.items;
}

/** 读取运费模板。 */
export async function listFreightTemplates(): Promise<FreightTemplate[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: FreightTemplate[] }>>(
    '/admin/freight-templates',
  );
  return response.data.data.items;
}
