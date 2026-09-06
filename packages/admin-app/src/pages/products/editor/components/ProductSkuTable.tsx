import type { JSX } from 'react';

export interface ProductSkuRow {
  skuId: number;
  skuCode: string;
  name: string;
  priceCents: number;
  quantity: number;
}

interface ProductSkuTableProps {
  rows: ProductSkuRow[];
}

/** SKU 规格只读表格，库存和价格调整由对应运营模块负责。 */
export function ProductSkuTable({ rows }: ProductSkuTableProps): JSX.Element {
  return (
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
      {rows.length ? (
        rows.map((sku) => (
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
  );
}
