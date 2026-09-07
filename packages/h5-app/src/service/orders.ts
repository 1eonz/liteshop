import type {
  Address,
  ApiEnvelope,
  FreightCalculateRequest,
  FreightCalculateResponse,
  OrderDetail,
  OrderCreateRequest,
  PageResponse,
  PaymentProvider,
  PaymentResponse,
} from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取收货地址。 */
export async function listAddresses(): Promise<Address[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: Address[] }>>('/user/addresses');
  return response.data.data.items;
}

export async function calculateFreight(
  input: FreightCalculateRequest,
): Promise<FreightCalculateResponse> {
  const response = await httpClient.post<ApiEnvelope<FreightCalculateResponse>>(
    '/orders/freight-calc',
    input,
  );
  return response.data.data;
}

export async function listOrders(page = 1): Promise<PageResponse<OrderDetail>> {
  const response = await httpClient.get<ApiEnvelope<PageResponse<OrderDetail>>>('/orders', {
    params: { page, pageSize: 20 },
  });
  return response.data.data;
}

export async function createOrder(
  input: OrderCreateRequest,
  requestId?: string,
): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>('/orders', input, {
    headers: requestId ? { 'X-Request-Id': requestId } : undefined,
  });
  return response.data.data;
}

export async function createPayment(
  orderId: number,
  provider: PaymentProvider,
  amountCents: number,
  requestId?: string,
): Promise<PaymentResponse> {
  const response = await httpClient.post<ApiEnvelope<PaymentResponse>>(
    '/payments',
    {
      orderId,
      provider,
      amountCents,
    },
    requestId ? { headers: { 'X-Request-Id': requestId } } : undefined,
  );
  return response.data.data;
}

export async function cancelOrder(orderId: number): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(`/orders/${orderId}/cancel`);
  return response.data.data;
}

export async function confirmOrder(orderId: number): Promise<OrderDetail> {
  const response = await httpClient.post<ApiEnvelope<OrderDetail>>(`/orders/${orderId}/confirm`);
  return response.data.data;
}

/** 读取一笔订单详情。 */
export async function getOrder(orderId: number): Promise<OrderDetail> {
  const response = await httpClient.get<ApiEnvelope<OrderDetail>>(`/orders/${orderId}`);
  return response.data.data;
}
