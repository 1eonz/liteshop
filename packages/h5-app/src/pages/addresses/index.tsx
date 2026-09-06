import type { FormEvent, JSX } from 'react';
import { useCallback, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Address, AddressInput } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import {
  createAddress,
  deleteAddress,
  listAddresses as listUserAddresses,
  updateAddress,
} from '../../service/user';
import { useSessionStore } from '../../store/session';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';

const blankAddress: AddressInput = {
  receiverName: '',
  phone: '',
  provinceCode: '',
  cityCode: '',
  districtCode: '',
  detail: '',
  isDefault: false,
};

/** 收货地址管理页面，新增、编辑、删除均通过幂等 API。 */
export function AddressesPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['addresses'],
    enabled: authenticated,
    queryFn: listUserAddresses,
  });
  const [editing, setEditing] = useState<Address | null>(null);
  const [form, setForm] = useState<AddressInput>(blankAddress);
  const [error, setError] = useState('');
  const saveMutation = useMutation({
    mutationFn: (input: AddressInput) =>
      editing ? updateAddress(editing.id, input) : createAddress(input),
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['addresses'] });
      setEditing(null);
      setForm(blankAddress);
    },
  });
  const deleteMutation = useMutation({
    mutationFn: deleteAddress,
    retry: 0,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['addresses'] });
    },
  });
  const save = useCallback(async () => {
    setError('');
    try {
      await saveMutation.mutateAsync(form);
    } catch {
      setError('地址保存失败，请检查填写内容。');
    }
  }, [form, saveMutation]);
  const remove = useCallback(
    async (addressId: number) => {
      setError('');
      try {
        await deleteMutation.mutateAsync(addressId);
      } catch {
        setError('地址删除失败，请稍后重试。');
      }
    },
    [deleteMutation],
  );
  const [runSave, saving] = useDebounceAction(save, 800);
  const [runDelete, deleting] = useDebounceAction(remove, 500);
  const edit = (address: Address): void => {
    setEditing(address);
    setForm({
      receiverName: address.receiverName,
      phone: address.phone,
      provinceCode: address.provinceCode,
      cityCode: address.cityCode,
      districtCode: address.districtCode,
      detail: address.detail,
      isDefault: address.isDefault,
    });
  };
  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void runSave();
  };
  if (!authenticated) return <Navigate to="/login" state={{ from: '/addresses' }} replace />;
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/me">
          ‹ 返回
        </Link>
        <h1>收货地址</h1>
      </header>
      {query.isLoading && <FeedbackState>地址加载中…</FeedbackState>}
      {query.isError && (
        <ErrorState onRetry={() => void query.refetch()}>地址加载失败，请重试。</ErrorState>
      )}
      <section className="address-list">
        {(query.data ?? []).map((address) => (
          <article className="address-item" key={address.id}>
            <div>
              <strong>{address.receiverName}</strong>
              <span>{address.phone}</span>
              {address.isDefault && <em>默认</em>}
              <p className="muted">{address.detail}</p>
            </div>
            <div className="row-actions">
              <button className="text-action" type="button" onClick={() => edit(address)}>
                编辑
              </button>
              <button
                className="text-action danger-action"
                type="button"
                disabled={deleting}
                onClick={() => void runDelete(address.id)}
              >
                删除
              </button>
            </div>
          </article>
        ))}
      </section>
      <form className="form-card address-form" onSubmit={submit}>
        <h2>{editing ? '编辑地址' : '新增地址'}</h2>
        {(
          ['receiverName', 'phone', 'provinceCode', 'cityCode', 'districtCode', 'detail'] as const
        ).map((field) => (
          <label key={field}>
            {
              {
                receiverName: '收货人',
                phone: '手机号',
                provinceCode: '省份编码',
                cityCode: '城市编码',
                districtCode: '区县编码',
                detail: '详细地址',
              }[field]
            }
            <input
              required
              value={form[field]}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  [field]: event.target.value,
                }))
              }
            />
          </label>
        ))}
        <label className="check-row">
          <input
            type="checkbox"
            checked={form.isDefault}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                isDefault: event.target.checked,
              }))
            }
          />
          设为默认地址
        </label>
        {error && (
          <p className="feedback error-state" role="alert">
            {error}
          </p>
        )}
        <div className="row-actions">
          <button className="primary-action" type="submit" disabled={saving}>
            {saving ? '保存中…' : '保存地址'}
          </button>
          {editing && (
            <button
              className="secondary-action"
              type="button"
              onClick={() => {
                setEditing(null);
                setForm(blankAddress);
              }}
            >
              取消编辑
            </button>
          )}
        </div>
      </form>
    </main>
  );
}
