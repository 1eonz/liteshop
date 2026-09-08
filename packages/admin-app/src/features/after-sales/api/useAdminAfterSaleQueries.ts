import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AfterSaleStatus, AfterSaleType, type AfterSaleRecord } from '@liteshop/shared-types';
import {
  auditAfterSale,
  completeAfterSale,
  listAdminAfterSales,
} from '../../../service/admin/after-sales';
import { isRecoverableApiError } from '../../../service/http';

const demoAfterSales: AfterSaleRecord[] = [
  {
    id: 1,
    afterSaleNo: 'AS202609080001',
    orderId: 1001,
    orderItemId: 2001,
    type: AfterSaleType.REFUND_ONLY,
    status: AfterSaleStatus.PENDING_REVIEW,
    amountCents: 12900,
    reason: '商品与描述不符',
    evidenceUrls: [],
    returnTrackingNo: '',
    auditReason: null,
    createdAt: '2026-09-08T09:00:00+08:00',
    updatedAt: '2026-09-08T09:00:00+08:00',
  },
];

/** 后台售后列表，开发环境仅在服务不可用时展示演示快照。 */
export function useAdminAfterSalesQuery(status?: AfterSaleStatus) {
  return useQuery({
    queryKey: ['admin-after-sales', status ?? 'all'],
    queryFn: async () => {
      try {
        return await listAdminAfterSales(status);
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return status ? demoAfterSales.filter((item) => item.status === status) : demoAfterSales;
      }
    },
  });
}

/** 后台售后审核与完成动作，禁止自动重试以避免重复退款。 */
export function useAdminAfterSaleMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-after-sales'] });
  };
  return {
    audit: useMutation({
      mutationFn: ({
        afterSaleId,
        approved,
        reason,
      }: {
        afterSaleId: number;
        approved: boolean;
        reason: string;
      }) => auditAfterSale(afterSaleId, approved, reason),
      retry: 0,
      onSuccess: refresh,
    }),
    complete: useMutation({
      mutationFn: (afterSaleId: number) => completeAfterSale(afterSaleId),
      retry: 0,
      onSuccess: refresh,
    }),
  };
}
