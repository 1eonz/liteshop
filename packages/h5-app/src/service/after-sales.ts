import type { AfterSaleCreateInput, AfterSaleRecord, ApiEnvelope } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取当前用户的售后单。 */
export async function listAfterSales(): Promise<AfterSaleRecord[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: AfterSaleRecord[] }>>('/after-sales');
  return response.data.data.items;
}

/** 读取售后详情并校验用户归属。 */
export async function getAfterSale(afterSaleId: number): Promise<AfterSaleRecord> {
  const response = await httpClient.get<ApiEnvelope<AfterSaleRecord>>(
    `/after-sales/${afterSaleId}`,
  );
  return response.data.data;
}

/** 创建售后申请，幂等键由统一 HTTP 拦截器生成。 */
export async function createAfterSale(input: AfterSaleCreateInput): Promise<AfterSaleRecord> {
  const response = await httpClient.post<ApiEnvelope<AfterSaleRecord>>('/after-sales', input);
  return response.data.data;
}

/** 提交退货物流单号。 */
export async function submitAfterSaleReturn(
  afterSaleId: number,
  trackingNo: string,
): Promise<AfterSaleRecord> {
  const response = await httpClient.put<ApiEnvelope<AfterSaleRecord>>(
    `/after-sales/${afterSaleId}/return`,
    { trackingNo },
  );
  return response.data.data;
}
