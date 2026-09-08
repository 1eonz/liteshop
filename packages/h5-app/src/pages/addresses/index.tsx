import type { FormEvent, JSX } from 'react';
import { useCallback, useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import type { Address, AddressInput } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { useSessionStore } from '../../store/session';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { useAddressBook } from '../../features/address';

const blankAddress: AddressInput = {
  receiverName: '',
  phone: '',
  provinceCode: '',
  cityCode: '',
  districtCode: '',
  detail: '',
  isDefault: false,
};

const REGION_OPTIONS = {
  provinces: [
    { code: '110000', name: '北京市' },
    { code: '310000', name: '上海市' },
    { code: '440000', name: '广东省' },
    { code: '330000', name: '浙江省' },
  ],
  cities: {
    '110000': [{ code: '110100', name: '北京市' }],
    '310000': [{ code: '310100', name: '上海市' }],
    '440000': [
      { code: '440100', name: '广州市' },
      { code: '440300', name: '深圳市' },
    ],
    '330000': [{ code: '330100', name: '杭州市' }],
  },
  districts: {
    '110100': [{ code: '110101', name: '东城区' }],
    '310100': [{ code: '310101', name: '黄浦区' }],
    '440100': [{ code: '440103', name: '荔湾区' }],
    '440300': [{ code: '440303', name: '罗湖区' }],
    '330100': [{ code: '330102', name: '上城区' }],
  },
} as const;

/** 收货地址管理页面，新增、编辑、删除均通过幂等 API。 */
export function AddressesPage(): JSX.Element {
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const {
    addressesQuery: query,
    saveAddressMutation,
    deleteAddressMutation,
  } = useAddressBook(authenticated);
  const [editing, setEditing] = useState<Address | null>(null);
  const [form, setForm] = useState<AddressInput>(blankAddress);
  const [error, setError] = useState('');
  const save = useCallback(async () => {
    setError('');
    try {
      await saveAddressMutation.mutateAsync({ addressId: editing?.id, input: form });
      setEditing(null);
      setForm(blankAddress);
    } catch {
      setError('地址保存失败，请检查填写内容。');
    }
  }, [editing?.id, form, saveAddressMutation]);
  const remove = useCallback(
    async (addressId: number) => {
      setError('');
      try {
        await deleteAddressMutation.mutateAsync(addressId);
      } catch {
        setError('地址删除失败，请稍后重试。');
      }
    },
    [deleteAddressMutation],
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
  const cities =
    REGION_OPTIONS.cities[form.provinceCode as keyof typeof REGION_OPTIONS.cities] ?? [];
  const districts =
    REGION_OPTIONS.districts[form.cityCode as keyof typeof REGION_OPTIONS.districts] ?? [];
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
        {(['receiverName', 'phone', 'detail'] as const).map((field) => (
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
        <label>
          省份
          <select
            required
            value={form.provinceCode}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                provinceCode: event.target.value,
                cityCode: '',
                districtCode: '',
              }))
            }
          >
            <option value="">请选择省份</option>
            {REGION_OPTIONS.provinces.map((item) => (
              <option value={item.code} key={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          城市
          <select
            required
            disabled={!form.provinceCode}
            value={form.cityCode}
            onChange={(event) =>
              setForm((current) => ({ ...current, cityCode: event.target.value, districtCode: '' }))
            }
          >
            <option value="">请选择城市</option>
            {cities.map((item) => (
              <option value={item.code} key={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          区县
          <select
            required
            disabled={!form.cityCode}
            value={form.districtCode}
            onChange={(event) =>
              setForm((current) => ({ ...current, districtCode: event.target.value }))
            }
          >
            <option value="">请选择区县</option>
            {districts.map((item) => (
              <option value={item.code} key={item.code}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
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
