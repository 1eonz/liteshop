import type { JSX } from 'react';
import { useMemo, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { createOrder } from '../../service/orders';
import { removeCartItem } from '../../service/cart';
import { useCartStore } from '../../store/cart';
import { formatPrice } from '@liteshop/shared-types';
import { useSessionStore } from '../../store/session';
import { ErrorState } from '@liteshop/shared-components';
import { useCheckoutAddressesQuery, useFreightQuery } from '../../features/checkout';

interface OrderConfirmLocationState {
  selectedIds?: number[];
}

/** 订单确认视图，展示地址、商品、运费和最终提交动作。 */
export function OrderConfirmPage(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();
  const allLines = useCartStore((state) => state.lines);
  const clearCart = useCartStore((state) => state.clear);
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const selectedIds = (location.state as OrderConfirmLocationState | null)?.selectedIds;
  const lines = useMemo(
    () =>
      selectedIds?.length ? allLines.filter((line) => selectedIds.includes(line.skuId)) : allLines,
    [allLines, selectedIds],
  );
  const [remark, setRemark] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [submitError, setSubmitError] = useState('');
  const addressesQuery = useCheckoutAddressesQuery(authenticated);
  const address = addressesQuery.data?.find((item) => item.isDefault) ?? addressesQuery.data?.[0];
  const productAmount = useMemo(
    () => lines.reduce((sum, line) => sum + line.priceCents * line.quantity, 0),
    [lines],
  );
  const freightQuery = useFreightQuery({
    items: lines.map((line) => ({
      skuId: line.skuId,
      quantity: line.quantity,
    })),
    provinceCode: address?.provinceCode,
    productAmount,
  });
  const freightAmount = freightQuery.data?.freightAmount ?? 0;
  const total = productAmount + freightAmount;
  const [submit, loading] = useDebounceAction(async () => {
    if (!address || !lines.length) return;
    if (!authenticated) {
      navigate('/login', { state: { from: '/order-confirm' } });
      return;
    }
    setSubmitError('');
    try {
      await createOrder({
        items: lines.map((line) => ({
          skuId: line.skuId,
          quantity: line.quantity,
          priceCents: line.priceCents,
        })),
        addressSnapshot: {
          receiverName: address.receiverName,
          phone: address.phone,
          provinceCode: address.provinceCode,
          cityCode: address.cityCode,
          districtCode: address.districtCode,
          detail: address.detail,
        },
        totalAmount: total,
        productAmount,
        freightAmount,
        remark: remark || undefined,
      });
      await Promise.all(lines.map((line) => removeCartItem(line.skuId)));
      clearCart();
      setSubmitted(true);
    } catch {
      setSubmitError('订单提交失败，请检查库存和金额后重试。');
    }
  }, 1000);
  if (submitted)
    return (
      <main className="trade-page success-page">
        <div className="success-mark" aria-hidden="true">
          ✓
        </div>
        <h1>订单已提交</h1>
        <p className="muted">感谢你的选择，我们会尽快为你准备商品。</p>
        <Link className="primary-action inline-action" to="/">
          继续逛逛
        </Link>
      </main>
    );
  if (!lines.length)
    return (
      <main className="trade-page">
        <p className="feedback">没有可结算的商品</p>
        <Link to="/cart">返回购物车</Link>
      </main>
    );
  if (addressesQuery.isError)
    return (
      <main className="trade-page">
        <ErrorState onRetry={() => void addressesQuery.refetch()}>
          收货地址读取失败，请先登录或重试。
        </ErrorState>
      </main>
    );
  return (
    <main className="trade-page">
      <header className="trade-header">
        <Link className="back-link" to="/cart">
          ‹ 返回
        </Link>
        <h1>确认订单</h1>
      </header>
      <section className="address-card">
        <div className="section-title">
          <h2>收货地址</h2>
          <button className="text-action" type="button" onClick={() => navigate('/cart')}>
            返回购物车
          </button>
        </div>
        {address ? (
          <>
            <p>
              <strong>{address.receiverName}</strong> {address.phone}
            </p>
            <p className="muted">{address.detail}</p>
          </>
        ) : (
          <p className="muted">请先添加收货地址</p>
        )}
      </section>
      <section className="checkout-items">
        <h2>商品清单</h2>
        {lines.map((line) => (
          <article className="cart-item" key={line.skuId}>
            <div className="cart-thumb" aria-hidden="true" />
            <div className="cart-line-content">
              <h3>商品 {line.skuId}</h3>
              <p className="muted">数量 × {line.quantity}</p>
            </div>
            <strong>{formatPrice(line.priceCents * line.quantity)}</strong>
          </article>
        ))}
      </section>
      <label className="remark-field">
        订单备注
        <textarea
          value={remark}
          onChange={(event) => setRemark(event.target.value)}
          placeholder="给商家留言（选填）"
          maxLength={500}
        />
      </label>
      <div className="summary-row">
        <span>商品金额</span>
        <span>{formatPrice(productAmount)}</span>
      </div>
      <div className="summary-row">
        <span>运费</span>
        <span>
          {freightQuery.isFetching
            ? '计算中…'
            : freightAmount
              ? formatPrice(freightAmount)
              : '包邮'}
        </span>
      </div>
      {freightQuery.isError && (
        <p className="feedback error-state" role="alert">
          运费计算失败，请重试后再提交。
        </p>
      )}
      {submitError && (
        <p className="feedback error-state" role="alert">
          {submitError}
        </p>
      )}
      <footer className="checkout-bar">
        <span>
          应付 <strong>{formatPrice(total)}</strong>
        </span>
        <button
          className="primary-action"
          type="button"
          disabled={loading || freightQuery.isFetching || freightQuery.isError || !address}
          onClick={() => void submit()}
        >
          {loading ? '提交中…' : '提交订单'}
        </button>
      </footer>
    </main>
  );
}
