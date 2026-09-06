import type { JSX } from 'react';
import type { ProductFormState } from '../model';

interface ProductBasicFieldsProps {
  form: ProductFormState;
  isCreate: boolean;
  onChange: (patch: Partial<ProductFormState>) => void;
}

/** SPU 基础字段与新建时的首个 SKU 字段。 */
export function ProductBasicFields({
  form,
  isCreate,
  onChange,
}: ProductBasicFieldsProps): JSX.Element {
  return (
    <>
      <div className="form-grid">
        <label>
          商品名称
          <input
            required
            value={form.name}
            onChange={(event) => onChange({ name: event.target.value })}
          />
        </label>
        <label>
          品牌
          <input value={form.brand} onChange={(event) => onChange({ brand: event.target.value })} />
        </label>
      </div>
      <label>
        副标题
        <input
          value={form.subtitle}
          onChange={(event) => onChange({ subtitle: event.target.value })}
        />
      </label>
      <label>
        商品描述
        <textarea
          value={form.description}
          onChange={(event) => onChange({ description: event.target.value })}
        />
      </label>
      <label>
        发布状态
        <select
          value={form.status}
          onChange={(event) =>
            onChange({ status: event.target.value as ProductFormState['status'] })
          }
        >
          <option value="DRAFT">草稿</option>
          <option value="ON_SHELF">已上架</option>
          <option value="OFF_SHELF">已下架</option>
        </select>
      </label>
      {isCreate && (
        <section className="sku-table" aria-labelledby="create-sku-title">
          <div className="section-heading">
            <h2 id="create-sku-title">首个 SKU</h2>
            <span className="muted">金额单位为整数分</span>
          </div>
          <div className="form-grid">
            <label>
              SKU 编码
              <input
                required
                value={form.skuCode}
                onChange={(event) => onChange({ skuCode: event.target.value })}
              />
            </label>
            <label>
              SKU 名称
              <input
                required
                value={form.skuName}
                onChange={(event) => onChange({ skuName: event.target.value })}
              />
            </label>
            <label>
              价格（分）
              <input
                required
                inputMode="numeric"
                value={form.priceCents}
                onChange={(event) => onChange({ priceCents: event.target.value })}
              />
            </label>
            <label>
              实物库存
              <input
                required
                inputMode="numeric"
                value={form.physicalStock}
                onChange={(event) => onChange({ physicalStock: event.target.value })}
              />
            </label>
          </div>
        </section>
      )}
    </>
  );
}
