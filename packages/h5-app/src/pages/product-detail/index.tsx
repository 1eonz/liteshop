import type { JSX } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { useProductQuery } from '../../hooks/useProductsQuery';
import { addCartItem } from '../../service/cart';
import {
  listFavoriteProductIds,
  listServerFavoriteProductIds,
  toggleFavoriteProduct,
  toggleServerFavoriteProduct,
} from '../../service/favorites';
import { useCartStore } from '../../store/cart';
import { formatPrice } from '@liteshop/shared-types';
import { listProductReviews } from '../../service/reviews';
import { useSessionStore } from '../../store/session';
import { ErrorState, FeedbackState } from '@liteshop/shared-components';
import { ProductGallery, DETAIL_SLIDES } from './components/ProductGallery';
import { ProductReviews } from './components/ProductReviews';
import { SkuDrawer } from './components/SkuDrawer';

/** 商品详情视图，SKU 抽屉是此页面的私有交互。 */
export function ProductDetailPage(): JSX.Element {
  const [skuOpen, setSkuOpen] = useState(false);
  const [imageIndex, setImageIndex] = useState(0);
  const params = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const productId = Number(params.productId ?? 1);
  const query = useProductQuery(productId);
  const queryClient = useQueryClient();
  const reviewsQuery = useQuery({
    queryKey: ['product-reviews', productId],
    queryFn: () => listProductReviews(productId),
  });
  const product = query.data;
  const [selectedSkuId, setSelectedSkuId] = useState<number | null>(null);
  const [favorite, setFavorite] = useState(() => listFavoriteProductIds().includes(productId));
  const addLine = useCartStore((state) => state.addLine);
  const authenticated = useSessionStore((state) => Boolean(state.accessToken));
  const favoritesQuery = useQuery({
    queryKey: ['favorites'],
    queryFn: listServerFavoriteProductIds,
    enabled: authenticated,
  });
  const closeSkuDrawer = useCallback(() => setSkuOpen(false), []);
  const selectedSku = product?.skus.find(
    (sku) => sku.skuId === (selectedSkuId ?? product.skus[0]?.skuId),
  );
  const [favoriteNotice, setFavoriteNotice] = useState('');
  const [actionNotice, setActionNotice] = useState('');
  useEffect(() => {
    if (authenticated) {
      if (favoritesQuery.data) setFavorite(favoritesQuery.data.includes(productId));
      return;
    }
    setFavorite(listFavoriteProductIds().includes(productId));
  }, [authenticated, favoritesQuery.data, productId]);
  const addAction = useCallback(async () => {
    if (!selectedSku) return;
    setActionNotice('');
    addLine({
      skuId: selectedSku.skuId,
      quantity: 1,
      priceCents: selectedSku.priceCents,
    });
    if (authenticated) {
      try {
        await addCartItem({
          skuId: selectedSku.skuId,
          quantity: 1,
          priceCents: selectedSku.priceCents,
        });
      } catch {
        setActionNotice('已加入本地购物车，但云端同步失败，请稍后重试。');
      }
    }
    closeSkuDrawer();
  }, [addLine, authenticated, closeSkuDrawer, selectedSku]);
  const [addToCart, loading] = useDebounceAction(addAction, 300);
  const [buyNow, buying] = useDebounceAction(async () => {
    await addAction();
    navigate('/cart');
  }, 300);
  const [toggleFavorite, togglingFavorite] = useDebounceAction(async () => {
    const nextValue = authenticated
      ? await toggleServerFavoriteProduct(productId)
      : toggleFavoriteProduct(productId);
    setFavorite(nextValue);
    setFavoriteNotice(nextValue ? '已加入收藏' : '已取消收藏');
    if (authenticated) void queryClient.invalidateQueries({ queryKey: ['favorites'] });
  }, 300);
  const moveImage = (offset: number): void => {
    setImageIndex((current) => (current + offset + DETAIL_SLIDES.length) % DETAIL_SLIDES.length);
  };
  if (query.isError)
    return (
      <main className="trade-page">
        <ErrorState>商品加载失败，请返回重试</ErrorState>
        <Link to="/">返回首页</Link>
      </main>
    );
  if (query.isLoading || !product)
    return (
      <main className="trade-page">
        <FeedbackState>商品加载中…</FeedbackState>
      </main>
    );
  const skuName = selectedSku?.name ?? '请选择规格';
  return (
    <main className="trade-page">
      <Link className="back-link" to="/">
        ‹ 返回
      </Link>
      <ProductGallery
        productName={product.name}
        imageIndex={imageIndex}
        onMove={moveImage}
        onSelect={setImageIndex}
      />
      <h1>{product.name}</h1>
      <p className="muted">{product.subtitle}</p>
      <strong className="detail-price">
        {formatPrice(selectedSku?.priceCents ?? product.minPrice)}
      </strong>
      <section className="detail-section">
        <div className="section-title">
          <h2>选择规格</h2>
          <span>库存 {selectedSku?.quantity ?? 0}</span>
        </div>
        <button className="sku-trigger" type="button" onClick={() => setSkuOpen(true)}>
          规格：{skuName} <span aria-hidden="true">›</span>
        </button>
      </section>
      <ProductReviews
        data={reviewsQuery.data}
        isLoading={reviewsQuery.isLoading}
        isError={reviewsQuery.isError}
        onRetry={() => void reviewsQuery.refetch()}
      />
      <section className="detail-section">
        <div className="section-title">
          <h2>商品详情</h2>
          <button
            className="text-action"
            type="button"
            disabled={togglingFavorite}
            onClick={() => void toggleFavorite()}
            aria-pressed={favorite}
          >
            {favorite ? '已收藏' : '收藏商品'}
          </button>
        </div>
        <p>{product.description}</p>
        {actionNotice && (
          <p className="action-feedback" role="status" aria-live="polite">
            {actionNotice}
          </p>
        )}
        {favoriteNotice && (
          <p className="action-feedback" role="status" aria-live="polite">
            {favoriteNotice}
          </p>
        )}
      </section>
      <div className="detail-actions">
        <button className="secondary-action" type="button" onClick={() => setSkuOpen(true)}>
          选择规格
        </button>
        <button
          className="primary-action"
          type="button"
          onClick={() => void addToCart()}
          disabled={loading || buying || !selectedSku}
        >
          {loading ? '加入中…' : '加入购物车'}
        </button>
        <button
          className="buy-action"
          type="button"
          onClick={() => void buyNow()}
          disabled={loading || buying || !selectedSku}
        >
          {buying ? '处理中…' : '立即购买'}
        </button>
      </div>
      <SkuDrawer
        open={skuOpen}
        product={product}
        selectedSku={selectedSku}
        loading={loading}
        onClose={closeSkuDrawer}
        onSelect={setSelectedSkuId}
        onConfirm={() => void addToCart()}
      />
    </main>
  );
}
