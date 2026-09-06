import { useQuery } from '@tanstack/react-query';
import type { FreightCalculateRequest } from '@liteshop/shared-types';
import { calculateFreight, listAddresses } from '../../../service/orders';

interface FreightQueryInput {
  items: FreightCalculateRequest['items'];
  provinceCode?: string;
  productAmount: number;
}

/** 订单确认页地址查询。 */
export function useCheckoutAddressesQuery(authenticated: boolean) {
  return useQuery({
    queryKey: ['addresses', authenticated],
    enabled: authenticated,
    queryFn: listAddresses,
  });
}

/** 订单确认页运费查询，金额保持整数分。 */
export function useFreightQuery(input: FreightQueryInput) {
  return useQuery({
    queryKey: ['freight', input.items, input.provinceCode, input.productAmount],
    enabled: Boolean(input.provinceCode && input.items.length),
    queryFn: () =>
      calculateFreight({
        items: input.items,
        provinceCode: input.provinceCode ?? '',
        productAmount: input.productAmount,
      }),
  });
}
