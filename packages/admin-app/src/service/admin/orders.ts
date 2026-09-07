import type {
  ApiEnvelope,
  OrderDetail,
  OrderManagementInput,
  PageResponse,
  ShipOrderInput,
} from '@liteshop/shared-types';
import { httpClient } from '../http';

/** 后台订单分页列表。 */
export async function listAdminOrders(page = 1, pageSize = 20): Promise<PageResponse<OrderDetail>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<OrderDetail>>>('/admin/orders', {
    params: { page, pageSize },
  });
  return response.data.data;
}

/** 后台发货。 */
export async function shipAdminOrder(orderId: number, input: ShipOrderInput): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/ship`,
    input,
  );
  return response.data.data;
}

/** 取消后台订单。 */
export async function cancelAdminOrder(orderId: number): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/cancel`,
  );
  return response.data.data;
}

/** 更新后台订单备注或地址。 */
export async function updateAdminOrder(
  orderId: number,
  input: OrderManagementInput,
): Promise<OrderDetail> {
  const response = await httpClient.put<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}`,
    input,
  );
  return response.data.data;
}

/** 修改待付款订单金额，金额单位为整数分。 */
export async function changeAdminOrderPrice(
  orderId: number,
  totalAmount: number,
): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(
    `/admin/orders/${orderId}/price`,
    { totalAmount },
  );
  return response.data.data;
}
