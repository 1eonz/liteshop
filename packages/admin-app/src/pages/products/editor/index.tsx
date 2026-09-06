import type { FormEvent, JSX } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import type { ProductCreateInput } from '@liteshop/shared-types';
import {
  useAdminProductQuery,
  useCreateAdminProductMutation,
  useUpdateAdminProductMutation,
} from '../../../features/catalog';
import { useDebounceAction } from '../../../hooks';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { ProductBasicFields } from './components/ProductBasicFields';
import { ProductSkuTable, type ProductSkuRow } from './components/ProductSkuTable';
import { INITIAL_PRODUCT_FORM, type ProductFormState } from './model';

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
  const [form, setForm] = useState<ProductFormState>(INITIAL_PRODUCT_FORM);
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
      skuCode: firstSku?.skuCode ?? INITIAL_PRODUCT_FORM.skuCode,
      skuName: firstSku?.name ?? INITIAL_PRODUCT_FORM.skuName,
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
        <FeedbackState>商品信息加载中…</FeedbackState>
      </div>
    );
  if (!isCreate && (productQuery.isError || !productQuery.data))
    return (
      <div className="editor-page">
        <ErrorState onRetry={() => void productQuery.refetch()}>
          商品信息加载失败，请刷新重试。
        </ErrorState>
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
  const skuRows: ProductSkuRow[] = product
    ? product.skus.map((sku) => ({
        skuId: sku.skuId,
        skuCode: sku.skuCode,
        name: sku.name,
        priceCents: sku.priceCents,
        quantity: sku.quantity,
      }))
    : [
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
        <ProductBasicFields
          form={form}
          isCreate={isCreate}
          onChange={(patch) => setForm((current) => ({ ...current, ...patch }))}
        />
        <ProductSkuTable rows={skuRows} />
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
