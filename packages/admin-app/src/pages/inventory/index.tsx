import type { JSX } from 'react';
import { useCallback, useState } from 'react';
import {
  useAdjustInventoryMutation,
  useDebounceAction,
  useInventoryLedgerQuery,
  useInventoryQuery,
} from '../../hooks';

/** 库存台账页面，实时展示三层库存并通过原因明确的表单调整。 */
export function InventoryPage(): JSX.Element {
  const inventoryQuery = useInventoryQuery();
  const adjustMutation = useAdjustInventoryMutation();
  const [editingSkuId, setEditingSkuId] = useState<number | null>(null);
  const [quantity, setQuantity] = useState('');
  const [reason, setReason] = useState('');
  const [adjustError, setAdjustError] = useState('');
  const [ledgerSkuId, setLedgerSkuId] = useState<number | null>(null);
  const ledgerQuery = useInventoryLedgerQuery(ledgerSkuId);
  const adjust = useCallback(
    async (skuId: number) => {
      const parsed = Number(quantity);
      if (!Number.isInteger(parsed) || parsed === 0 || !reason.trim()) {
        setAdjustError('请输入非零整数和调整原因。');
        return;
      }
      setAdjustError('');
      try {
        await adjustMutation.mutateAsync({
          skuId,
          quantity: parsed,
          reason: reason.trim(),
        });
        setEditingSkuId(null);
        setQuantity('');
        setReason('');
      } catch {
        setAdjustError('库存调整失败，请检查权限、库存和原因后重试。');
      }
    },
    [adjustMutation, quantity, reason],
  );
  const [runAdjust, adjusting] = useDebounceAction(adjust, 500);
  if (inventoryQuery.isLoading)
    return (
      <div className="editor-page">
        <div className="feedback">库存加载中…</div>
      </div>
    );
  if (inventoryQuery.isError)
    return (
      <div className="editor-page">
        <div className="feedback error-state" role="alert">
          库存加载失败，请刷新重试。
        </div>
      </div>
    );
  const rows = inventoryQuery.data?.items ?? [];
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>库存管理</p>
          <h1>库存台账</h1>
        </div>
        <button
          type="button"
          disabled={inventoryQuery.isFetching}
          onClick={() => void inventoryQuery.refetch()}
        >
          {inventoryQuery.isFetching ? '刷新中…' : '刷新'}
        </button>
      </header>
      {adjustError && (
        <p className="feedback error-state" role="alert">
          {adjustError}
        </p>
      )}
      <section className="editor-form inventory-list" aria-label="库存台账">
        <div className="sku-row sku-head">
          <span>SKU</span>
          <span>实物库存</span>
          <span>可售库存</span>
          <span>锁定库存</span>
          <span>操作</span>
        </div>
        {rows.length ? (
          rows.map((row) => (
            <article className="sku-row inventory-row" key={row.skuId}>
              <span>
                <strong>{row.name}</strong>
                <small>{row.skuCode}</small>
                {row.warning && <em className="warning-badge">低库存</em>}
              </span>
              <span>{row.physicalStock}</span>
              <span>{row.availableStock}</span>
              <span>{row.lockedStock}</span>
              <span className="row-actions">
                {editingSkuId === row.skuId ? (
                  <div className="inline-adjust">
                    <input
                      aria-label="调整数量"
                      type="number"
                      value={quantity}
                      onChange={(event) => setQuantity(event.target.value)}
                      placeholder="±数量"
                    />
                    <input
                      aria-label="调整原因"
                      value={reason}
                      onChange={(event) => setReason(event.target.value)}
                      placeholder="原因"
                    />
                    <button
                      type="button"
                      disabled={adjusting}
                      onClick={() => void runAdjust(row.skuId)}
                    >
                      {adjusting ? '保存中…' : '保存'}
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      disabled={adjusting}
                      onClick={() => setEditingSkuId(null)}
                    >
                      取消
                    </button>
                  </div>
                ) : (
                  <>
                    <button type="button" onClick={() => setEditingSkuId(row.skuId)}>
                      调整
                    </button>
                    <button
                      className="ghost-button"
                      type="button"
                      onClick={() => setLedgerSkuId(row.skuId)}
                    >
                      流水
                    </button>
                  </>
                )}
              </span>
            </article>
          ))
        ) : (
          <div className="feedback">暂无库存数据</div>
        )}
      </section>
      {ledgerSkuId !== null && (
        <section className="panel ledger-panel">
          <div className="panel-title">
            <h2>库存流水 · SKU {ledgerSkuId}</h2>
            <button className="ghost-button" type="button" onClick={() => setLedgerSkuId(null)}>
              关闭
            </button>
          </div>
          {ledgerQuery.isLoading ? (
            <div className="feedback">流水加载中…</div>
          ) : ledgerQuery.data?.length ? (
            ledgerQuery.data.map((entry) => (
              <div className="ledger-row" key={entry.id}>
                <span>{entry.eventType}</span>
                <strong>{entry.quantity > 0 ? `+${entry.quantity}` : entry.quantity}</strong>
                <span>{entry.reason || entry.referenceNo || '系统操作'}</span>
                <time dateTime={entry.createdAt}>
                  {new Date(entry.createdAt).toLocaleString('zh-CN')}
                </time>
              </div>
            ))
          ) : (
            <div className="feedback">暂无流水</div>
          )}
        </section>
      )}
    </div>
  );
}
