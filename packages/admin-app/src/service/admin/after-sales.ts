import type { AfterSaleRecord, AfterSaleStatus, ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 读取后台售后单，可按状态筛选。 */
export async function listAdminAfterSales(status?: AfterSaleStatus): Promise<AfterSaleRecord[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: AfterSaleRecord[] }>>(
    '/admin/after-sales',
    { params: status ? { status } : undefined },
  );
  return response.data.data.items;
}

/** 审核售后申请，approved 为 true 表示通过。 */
export async function auditAfterSale(
  afterSaleId: number,
  approved: boolean,
  reason: string,
): Promise<AfterSaleRecord> {
  const response = await httpClient.put<ApiEnvelope<AfterSaleRecord>>(
    `/admin/after-sales/${afterSaleId}/audit`,
    { approved, reason },
  );
  return response.data.data;
}

/** 确认退货并完成退款或换货入库。 */
export async function completeAfterSale(afterSaleId: number): Promise<AfterSaleRecord> {
  const response = await httpClient.put<ApiEnvelope<AfterSaleRecord>>(
    `/admin/after-sales/${afterSaleId}/complete`,
  );
  return response.data.data;
}
