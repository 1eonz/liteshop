import type { JSX } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import type { CartItem } from '@liteshop/shared-types';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { getCart, removeCartItem, updateCartItem } from '../../service/cart';
import { isRecoverableApiError } from '../../service/http';
import { useCartStore } from '../../store/cart';
import { formatPrice } from '../../utils/format-price';
import { toLocalCartItem } from '../../features/cart';
import { useSessionStore } from '../../store/session';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { CartLineItem } from './components/CartLineItem';

const EMPTY_CART_ITEMS: CartItem[] = [];

/** 购物车视图，提交动作统一走防抖 Hook。 */
export function CartPage(): JSX.Element {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const localLines = useCartStore((state) => state.lines);
  const updateLocal = useCartStore((state) => state.updateLine);
  const removeLocal = useCartStore((state) => state.removeLine);
  const setLines = useCartStore((state) => state.setLines);
  const isAuthenticated = useSessionStore((state) => Boolean(state.accessToken));
  const hydratedRef = useRef(false);
  const [selectedIds, setSelectedIds] = useState<number[]>(localLines.map((line) => line.skuId));
  const [actionFeedback, setActionFeedback] = useState('');
  useEffect(() => {
    if (!isAuthenticated) hydratedRef.current = false;
  }, [isAuthenticated]);
  const cartQuery = useQuery({
    queryKey: ['cart', isAuthenticated],
    enabled: isAuthenticated,
    queryFn: async () => {
      try {
        return await getCart();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return { items: [] };
      }
    },
  });
  useEffect(() => {
    if (!isAuthenticated || !cartQuery.data || hydratedRef.current) return;
    const remoteLines = cartQuery.data.items.map((item) => ({
      skuId: item.skuId,
      quantity: item.quantity,
      priceCents: item.priceCents,
    }));
    setLines(remoteLines);
    setSelectedIds(remoteLines.map((line) => line.skuId));
    hydratedRef.current = true;
  }, [cartQuery.data, isAuthenticated, setLines]);

  const remoteItems = cartQuery.data?.items ?? EMPTY_CART_ITEMS;
  const localBySku = useMemo(
    () => new Map(localLines.map((line) => [line.skuId, line])),
    [localLines],
  );
  const lines = useMemo(() => {
    if (!isAuthenticated) return localLines.map(toLocalCartItem);
    const remoteSkuIds = new Set(remoteItems.map((item) => item.skuId));
    const synced = remoteItems.map((item) => {
      const local = localBySku.get(item.skuId);
      return local ? { ...item, quantity: local.quantity, priceCents: local.priceCents } : item;
    });
    const localOnly = localLines
      .filter((line) => !remoteSkuIds.has(line.skuId))
      .map(toLocalCartItem);
    return [...synced, ...localOnly];
  }, [isAuthenticated, localBySku, localLines, remoteItems]);

  useEffect(() => {
    setSelectedIds((ids) => {
      const nextIds = ids.filter((id) => lines.some((line) => line.skuId === id));
      return nextIds.length === ids.length ? ids : nextIds;
    });
  }, [lines]);

  const selected = selectedIds.length > 0 && selectedIds.length === lines.length;
  const total = useMemo(
    () =>
      lines
        .filter((line) => selectedIds.includes(line.skuId))
        .reduce((sum, line) => sum + line.priceCents * line.quantity, 0),
    [lines, selectedIds],
  );
  const [changeQuantity, changing] = useDebounceAction(async (skuId: number, quantity: number) => {
    const line = lines.find((item) => item.skuId === skuId);
    if (!line) return;
    updateLocal(skuId, quantity);
    setActionFeedback(`${line.name} 数量已更新为 ${quantity}`);
    if (isAuthenticated) {
      try {
        await updateCartItem(skuId, {
          skuId,
          quantity,
          priceCents: line.priceCents,
        });
      } catch {
        updateLocal(skuId, line.quantity);
        setActionFeedback(`${line.name} 数量同步失败，已恢复原数量`);
        void queryClient.invalidateQueries({ queryKey: ['cart', true] });
      }
    }
  }, 300);
  const [remove, removing] = useDebounceAction(async (skuId: number) => {
    const line = lines.find((item) => item.skuId === skuId);
    if (!line) return;
    removeLocal(skuId);
    setSelectedIds((ids) => ids.filter((id) => id !== skuId));
    setActionFeedback(`${line.name} 已从购物车移除`);
    if (isAuthenticated) {
      try {
        await removeCartItem(skuId);
      } catch {
        updateLocal(skuId, line.quantity);
        setSelectedIds((ids) => (ids.includes(skuId) ? ids : [...ids, skuId]));
        setActionFeedback(`${line.name} 移除失败，商品已恢复`);
        void queryClient.invalidateQueries({ queryKey: ['cart', true] });
      }
    }
  }, 500);
  const [checkout, checkingOut] = useDebounceAction(
    async () => navigate('/order/confirm', { state: { selectedIds } }),
    800,
  );
  if (isAuthenticated && cartQuery.isLoading)
    return (
      <main className="trade-page">
        <FeedbackState>购物车加载中…</FeedbackState>
      </main>
    );
  if (isAuthenticated && cartQuery.isError)
    return (
      <main className="trade-page">
        <ErrorState onRetry={() => void cartQuery.refetch()}>购物车读取失败，请重试。</ErrorState>
      </main>
    );
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/">
          ‹ 返回
        </Link>
        <h1>购物车</h1>
      </header>
      {actionFeedback && (
        <p className="action-feedback" role="status" aria-live="polite">
          {actionFeedback}
        </p>
      )}
      {lines.length === 0 ? (
        <section className="empty-state">
          <div className="empty-illustration" aria-hidden="true">
            ＋
          </div>
          <h2>购物车还是空的</h2>
          <p className="muted">去挑几件喜欢的好物吧</p>
          <Link className="primary-action inline-action" to="/">
            去逛逛
          </Link>
        </section>
      ) : (
        <>
          <label className="check-row">
            <input
              type="checkbox"
              checked={selected}
              onChange={(event) =>
                setSelectedIds(event.target.checked ? lines.map((line) => line.skuId) : [])
              }
            />{' '}
            全选 <span className="muted">共 {lines.length} 件</span>
          </label>
          <section className="cart-list" aria-label="购物车商品">
            {lines.map((line) => (
              <CartLineItem
                key={line.skuId}
                line={line}
                selected={selectedIds.includes(line.skuId)}
                changing={changing}
                removing={removing}
                onToggleSelected={(checked) =>
                  setSelectedIds((ids) =>
                    checked ? [...ids, line.skuId] : ids.filter((id) => id !== line.skuId),
                  )
                }
                onChangeQuantity={(quantity) => void changeQuantity(line.skuId, quantity)}
                onRemove={() => void remove(line.skuId)}
              />
            ))}
          </section>
          <footer className="checkout-bar">
            <span>
              合计 <strong>{formatPrice(total)}</strong>
            </span>
            <button
              className="primary-action"
              type="button"
              disabled={!selectedIds.length || checkingOut}
              onClick={() => void checkout()}
            >
              {checkingOut ? '处理中…' : '去结算'}
            </button>
          </footer>
        </>
      )}
    </main>
  );
}
