import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { AddressInput } from '@liteshop/shared-types';
import { createAddress, deleteAddress, listAddresses, updateAddress } from '../../../service/user';

interface SaveAddressInput {
  addressId?: number;
  input: AddressInput;
}

/** 地址簿服务端状态，集中处理缓存失效与禁止写操作重试。 */
export function useAddressBook(authenticated: boolean) {
  const queryClient = useQueryClient();
  const addressesQuery = useQuery({
    queryKey: ['addresses'],
    enabled: authenticated,
    queryFn: listAddresses,
  });
  const invalidateAddresses = (): Promise<void> =>
    queryClient.invalidateQueries({ queryKey: ['addresses'] });
  const saveAddressMutation = useMutation({
    mutationFn: ({ addressId, input }: SaveAddressInput) =>
      addressId ? updateAddress(addressId, input) : createAddress(input),
    retry: 0,
    onSuccess: invalidateAddresses,
  });
  const deleteAddressMutation = useMutation({
    mutationFn: deleteAddress,
    retry: 0,
    onSuccess: invalidateAddresses,
  });

  return { addressesQuery, saveAddressMutation, deleteAddressMutation };
}
