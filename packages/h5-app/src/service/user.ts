import type { Address, AddressInput, ApiEnvelope, UserProfile } from '@liteshop/shared-types';
import { httpClient } from './http';

/** 读取当前用户资料。 */
export async function getProfile(): Promise<UserProfile> {
  const response = await httpClient.get<ApiEnvelope<UserProfile>>('/user/me');
  return response.data.data;
}

/** 读取当前用户地址。 */
export async function listAddresses(): Promise<Address[]> {
  const response = await httpClient.get<ApiEnvelope<{ items: Address[] }>>('/user/addresses');
  return response.data.data.items;
}

/** 新增收货地址。 */
export async function createAddress(input: AddressInput): Promise<Address> {
  const response = await httpClient.post<ApiEnvelope<Address>>('/user/addresses', input);
  return response.data.data;
}

/** 更新收货地址。 */
export async function updateAddress(
  addressId: number,
  input: Partial<AddressInput>,
): Promise<Address> {
  const response = await httpClient.put<ApiEnvelope<Address>>(
    `/user/addresses/${addressId}`,
    input,
  );
  return response.data.data;
}

/** 删除收货地址。 */
export async function deleteAddress(addressId: number): Promise<void> {
  await httpClient.delete<ApiEnvelope<{ deleted: boolean }>>(`/user/addresses/${addressId}`);
}
