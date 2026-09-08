import type {
  ApiEnvelope,
  FreightTemplate,
  InventoryLedgerEntry,
  InventoryRow,
  PageResponse,
} from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 运费模板计费项写入参数，金额单位为整数分。 */
export interface FreightTemplateItemInput {
  regionCodes: string[];
  firstUnit: number;
  firstFee: number;
  additionalUnit: number;
  additionalFee: number;
  freeCondition?: Record<string, unknown> | null;
}

/** 运费模板写入参数。 */
export interface FreightTemplateInput {
  name: string;
  type: FreightTemplate['type'];
  isDefault: boolean;
  enabled: boolean;
  items?: FreightTemplateItemInput[];
}

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

/** 创建运费模板。 */
export async function createFreightTemplate(input: FreightTemplateInput): Promise<FreightTemplate> {
  const response = await httpClient.post<ApiEnvelope<FreightTemplate>>(
    '/admin/freight-templates',
    input,
  );
  return response.data.data;
}

/** 更新运费模板基础信息。 */
export async function updateFreightTemplate(
  templateId: number,
  input: Partial<FreightTemplateInput>,
): Promise<FreightTemplate> {
  const response = await httpClient.put<ApiEnvelope<FreightTemplate>>(
    `/admin/freight-templates/${templateId}`,
    input,
  );
  return response.data.data;
}

/** 删除运费模板。 */
export async function deleteFreightTemplate(templateId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ deleted: boolean }>>(
    `/admin/freight-templates/${templateId}`,
  );
}

/** 新增模板地区计费项。 */
export async function addFreightTemplateItem(
  templateId: number,
  input: FreightTemplateItemInput,
): Promise<FreightTemplate> {
  const response = await httpClient.post<ApiEnvelope<FreightTemplate>>(
    `/admin/freight-templates/${templateId}/items`,
    input,
  );
  return response.data.data;
}

/** 更新模板地区计费项。 */
export async function updateFreightTemplateItem(
  templateId: number,
  itemId: number,
  input: Partial<FreightTemplateItemInput>,
): Promise<FreightTemplate> {
  const response = await httpClient.put<ApiEnvelope<FreightTemplate>>(
    `/admin/freight-templates/${templateId}/items/${itemId}`,
    input,
  );
  return response.data.data;
}

/** 删除模板地区计费项。 */
export async function deleteFreightTemplateItem(templateId: number, itemId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ deleted: boolean }>>(
    `/admin/freight-templates/${templateId}/items/${itemId}`,
  );
}
