import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { InventoryLedgerEntry, InventoryRow, PageResponse } from '@liteshop/shared-types';
import {
  adjustInventory,
  listInventory,
  listInventoryLedger,
} from '../../../service/admin/inventory';
import { isRecoverableApiError } from '../../../service/http';

const demoInventory: PageResponse<InventoryRow> = {
  items: [
    {
      skuId: 1,
      skuCode: 'CUP-480',
      name: '晨雾保温杯 / 标准款',
      physicalStock: 100,
      availableStock: 96,
      lockedStock: 4,
      safetyStock: 10,
      warning: false,
    },
    {
      skuId: 2,
      skuCode: 'HOODIE-M',
      name: '云朵卫衣 / M',
      physicalStock: 58,
      availableStock: 56,
      lockedStock: 2,
      safetyStock: 60,
      warning: true,
    },
  ],
  meta: { page: 1, pageSize: 50, total: 2, hasNext: false },
};

/** 后台库存查询。 */
export function useInventoryQuery() {
  return useQuery({
    queryKey: ['admin-inventory'],
    queryFn: async () => {
      try {
        return await listInventory();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return demoInventory;
      }
    },
  });
}

/** 指定 SKU 库存流水查询。 */
export function useInventoryLedgerQuery(skuId: number | null) {
  return useQuery<InventoryLedgerEntry[]>({
    queryKey: ['inventory-ledger', skuId],
    queryFn: () => listInventoryLedger(skuId as number),
    enabled: skuId !== null,
  });
}

/** 后台库存调整 mutation。 */
export function useAdjustInventoryMutation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      skuId,
      quantity,
      reason,
    }: {
      skuId: number;
      quantity: number;
      reason: string;
    }) => adjustInventory(skuId, quantity, reason),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['admin-inventory'] });
      void queryClient.invalidateQueries({ queryKey: ['admin-dashboard'] });
    },
  });
}
