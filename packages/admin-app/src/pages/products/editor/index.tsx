import type { FormEvent, JSX } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  useAdminProductQuery,
  useCreateAdminProductMutation,
  useDebounceAction,
  useUpdateAdminProductMutation,
} from '../../../hooks';
import type { ProductCreateInput } from '../../../service/admin';

interface ProductFormState {
  name: string;
  subtitle: string;
  brand: string;
  description: string;
  status: 'DRAFT' | 'ON_SHELF' | 'OFF_SHELF';
  skuCode: string;
  skuName: string;
  priceCents: string;
  physicalStock: string;
}

const initialForm: ProductFormState = {
  name: '',
  subtitle: '',
  brand: '',
  description: '',
  status: 'DRAFT',
  skuCode: 'NEW-SKU-001',
  skuName: '标准款',
  priceCents: '12900',
  physicalStock: '100',
};

/** SPU/SKU 商品编辑页面，SPU 写入走 mutation，SKU 库存由库存页独立维护。 */
export function ProductEditorPage(): JSX.Element {
  const params = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const hasProductParam = params.productId !== undefined;
  const parsedProductId = params.productId ? Number(params.productId) : null;
  const productId =
    parsedProductId !== null && Number.isInteger(parsedProductId) && parsedProductId > 0
      ? parsedProductId
      : null;
  const isCreate = !hasProductParam;
  const productQuery = useAdminProductQuery(productId);
  const createMutation = useCreateAdminProductMutation();
  const updateMutation = useUpdateAdminProductMutation();
  const [form, setForm] = useState<ProductFormState>(initialForm);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');

  useEffect(() => {
    const product = productQuery.data;
    if (!product) return;
    const firstSku = product.skus[0];
    setForm({
      name: product.name,
      subtitle: product.subtitle,
      brand: product.brand,
      description: product.description,
      status: product.status,
      skuCode: firstSku?.skuCode ?? initialForm.skuCode,
      skuName: firstSku?.name ?? initialForm.skuName,
      priceCents: String(firstSku?.priceCents ?? 0),
      physicalStock: String(firstSku?.quantity ?? 0),
    });
  }, [productQuery.data]);

  const saveProduct = useCallback(async () => {
    setSaved(false);
    setSaveError('');
    try {
      if (isCreate) {
        const priceCents = Number(form.priceCents);
        const physicalStock = Number(form.physicalStock);
        if (
          !Number.isInteger(priceCents) ||
          priceCents < 0 ||
          !Number.isInteger(physicalStock) ||
          physicalStock < 0
        ) {
          setSaveError('价格和库存必须填写非负整数。');
          return;
        }
        const input: ProductCreateInput = {
          name: form.name,
          subtitle: form.subtitle,
          brand: form.brand,
          description: form.description,
          status: form.status,
          skus: [
            {
              code: form.skuCode,
              name: form.skuName,
              priceCents,
              physicalStock,
              specs: {},
            },
          ],
        };
        const product = await createMutation.mutateAsync(input);
        navigate(`/products/edit/${product.id}`, { replace: true });
      } else if (productId !== null) {
        await updateMutation.mutateAsync({
          productId,
          input: {
            name: form.name,
            subtitle: form.subtitle,
            brand: form.brand,
            description: form.description,
            status: form.status,
          },
        });
        setSaved(true);
      }
    } catch {
      setSaveError('商品保存失败，请检查权限或网络后重试。');
    }
  }, [createMutation, form, isCreate, navigate, productId, updateMutation]);
  const [save, loading] = useDebounceAction(saveProduct, 500);

  const submit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    void save();
  };

  if (!isCreate && productQuery.isLoading)
    return (
      <div className="editor-page">
        <div className="feedback">商品信息加载中…</div>
      </div>
    );
  if (!isCreate && (productQuery.isError || !productQuery.data))
    return (
      <div className="editor-page">
        <div className="feedback error-state" role="alert">
          商品信息加载失败，请刷新重试。
        </div>
      </div>
    );
  if (!isCreate && productId === null)
    return (
      <div className="editor-page">
        <div className="feedback error-state" role="alert">
          商品 ID 无效。
        </div>
      </div>
    );
  const product = productQuery.data;
  const skuRows = product?.skus ?? [
    {
      skuId: 0,
      skuCode: form.skuCode,
      name: form.skuName,
      priceCents: Number(form.priceCents) || 0,
      quantity: Number(form.physicalStock) || 0,
    },
  ];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>{isCreate ? '商品中心 · 新建 SPU' : `商品管理 · SPU ${product?.id ?? ''}`}</p>
          <h1>{isCreate ? '新建商品' : '编辑商品'}</h1>
        </div>
        <button
          type="button"
          disabled={loading || createMutation.isPending || updateMutation.isPending}
          onClick={() => void save()}
        >
          {loading || createMutation.isPending || updateMutation.isPending ? '保存中…' : '保存商品'}
        </button>
      </header>
      <form className="editor-form" onSubmit={submit}>
        <div className="form-grid">
          <label>
            商品名称
            <input
              required
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
          </label>
          <label>
            品牌
            <input
              value={form.brand}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  brand: event.target.value,
                }))
              }
            />
          </label>
        </div>
        <label>
          副标题
          <input
            value={form.subtitle}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                subtitle: event.target.value,
              }))
            }
          />
        </label>
        <label>
          商品描述
          <textarea
            value={form.description}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                description: event.target.value,
              }))
            }
          />
        </label>
        <label>
          发布状态
          <select
            value={form.status}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                status: event.target.value as ProductFormState['status'],
              }))
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
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      skuCode: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                SKU 名称
                <input
                  required
                  value={form.skuName}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      skuName: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                价格（分）
                <input
                  required
                  inputMode="numeric"
                  value={form.priceCents}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      priceCents: event.target.value,
                    }))
                  }
                />
              </label>
              <label>
                实物库存
                <input
                  required
                  inputMode="numeric"
                  value={form.physicalStock}
                  onChange={(event) =>
                    setForm((current) => ({
                      ...current,
                      physicalStock: event.target.value,
                    }))
                  }
                />
              </label>
            </div>
          </section>
        )}
        <section className="sku-table" aria-labelledby="sku-title">
          <div className="section-heading">
            <h2 id="sku-title">SKU 规格</h2>
            <span className="muted">价格和库存请在对应模块调整</span>
          </div>
          <div className="sku-row sku-head">
            <span>规格</span>
            <span>编码</span>
            <span>价格（分）</span>
            <span>可售库存</span>
          </div>
          {skuRows.length ? (
            skuRows.map((sku) => (
              <div className="sku-row" key={sku.skuId}>
                <span>{sku.name}</span>
                <span>{sku.skuCode}</span>
                <span>{sku.priceCents}</span>
                <span>{sku.quantity}</span>
              </div>
            ))
          ) : (
            <div className="feedback">暂无 SKU</div>
          )}
        </section>
        {saved && (
          <p className="success-message" role="status">
            已保存
          </p>
        )}
        {saveError && (
          <p className="feedback error-state" role="alert">
            {saveError}
          </p>
        )}
        <button
          className="form-submit"
          type="submit"
          disabled={loading || createMutation.isPending || updateMutation.isPending}
        >
          {loading || createMutation.isPending || updateMutation.isPending ? '保存中…' : '保存商品'}
        </button>
      </form>
    </div>
  );
}
