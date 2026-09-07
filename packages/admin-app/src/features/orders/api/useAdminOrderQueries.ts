import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { OrderStatus } from '@liteshop/shared-types';
import type {
  OrderDetail,
  OrderManagementInput,
  PageResponse,
  ShipOrderInput,
} from '@liteshop/shared-types';
import {
  cancelAdminOrder,
  changeAdminOrderPrice,
  listAdminOrders,
  shipAdminOrder,
  updateAdminOrder,
} from '../../../service/admin/orders';
import { isRecoverableApiError } from '../../../service/http';

const demoOrders: PageResponse<OrderDetail> = {
  items: [
    {
      id: 1,
      orderNo: 'LS202609050001',
      status: OrderStatus.PAID,
      totalAmount: 12900,
      productAmount: 12900,
      freightAmount: 0,
      discountAmount: 0,
      refundStatus: 'NONE',
      paidAmount: 12900,
      paidAt: '2026-09-05T08:00:00+08:00',
      shippedAt: null,
      completedAt: null,
      cancelledAt: null,
      cancelReason: null,
      addressSnapshot: { receiverName: '张三', detail: '杭州市西湖区文三路 1 号' },
      remark: '',
      shippingCompanyCode: '',
      trackingNo: '',
      items: [
        {
          id: 1,
          skuId: 1,
          productId: 1,
          productName: '晨雾保温杯',
          skuCode: 'CUP-480',
          skuName: '480ml',
          specValues: { 容量: '480ml' },
          productImage: '',
          quantity: 1,
          priceCents: 12900,
          weightGrams: 420,
          discountAmount: 0,
          totalAmount: 12900,
        },
      ],
      createdAt: '2026-09-05T08:00:00+08:00',
    },
  ],
  meta: { page: 1, pageSize: 20, total: 1, hasNext: false },
};

/** 后台订单查询。 */
export function useAdminOrdersQuery() {
  return useQuery({
    queryKey: ['admin-orders'],
    queryFn: async () => {
      try {
        return await listAdminOrders();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoOrders;
      }
    },
  });
}

/** 后台发货 mutation。 */
export function useShipAdminOrderMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ orderId, input }: { orderId: number; input: ShipOrderInput }) =>
      shipAdminOrder(orderId, input),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
    },
  });
}

/** 后台订单取消、备注编辑和改价动作。 */
export function useAdminOrderMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
  };
  return {
    cancel: useMutation({ mutationFn: cancelAdminOrder, retry: 0, onSuccess: refresh }),
    update: useMutation({
      mutationFn: ({ orderId, input }: { orderId: number; input: OrderManagementInput }) =>
        updateAdminOrder(orderId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    changePrice: useMutation({
      mutationFn: ({ orderId, totalAmount }: { orderId: number; totalAmount: number }) =>
        changeAdminOrderPrice(orderId, totalAmount),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}
