import type { JSX, KeyboardEvent as ReactKeyboardEvent } from 'react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useDebounceAction } from '../../hooks/useDebounceAction';
import { useProductQuery } from '../../hooks/useProductsQuery';
import { addCartItem } from '../../service/cart';
import {
  listFavoriteProductIds,
  toggleFavoriteProduct,
  toggleServerFavoriteProduct,
} from '../../service/favorites';
import { useCartStore } from '../../store/cart';
import { formatPrice } from '../../utils/format-price';
import { listProductReviews } from '../../service/reviews';

const detailSlides = ['商品主图', '生活场景', '细节展示'];

/** 商品详情视图，SKU 抽屉是此页面的私有交互。 */
export function ProductDetailPage(): JSX.Element {
  const [skuOpen, setSkuOpen] = useState(false);
  const [imageIndex, setImageIndex] = useState(0);
  const drawerRef = useRef<HTMLElement | null>(null);
  const params = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const productId = Number(params.productId ?? 1);
  const query = useProductQuery(productId);
  const reviewsQuery = useQuery({
    queryKey: ['product-reviews', productId],
    queryFn: () => listProductReviews(productId),
  });
  const product = query.data;
  const [selectedSkuId, setSelectedSkuId] = useState<number | null>(null);
  const [favorite, setFavorite] = useState(() => listFavoriteProductIds().includes(productId));
  const addLine = useCartStore((state) => state.addLine);
  const selectedSku = product?.skus.find(
    (sku) => sku.skuId === (selectedSkuId ?? product.skus[0]?.skuId),
  );
  const [favoriteNotice, setFavoriteNotice] = useState('');
  const addAction = useCallback(async () => {
    if (!selectedSku) return;
    addLine({
      skuId: selectedSku.skuId,
      quantity: 1,
      priceCents: selectedSku.priceCents,
    });
    if (window.localStorage.getItem('liteshop.accessToken')) {
      try {
        await addCartItem({
          skuId: selectedSku.skuId,
          quantity: 1,
          priceCents: selectedSku.priceCents,
        });
      } catch {
        /* 本地购物车仍可继续使用 */
      }
    }
    setSkuOpen(false);
  }, [addLine, selectedSku]);
  const [addToCart, loading] = useDebounceAction(addAction, 300);
  const [buyNow, buying] = useDebounceAction(async () => {
    await addAction();
    navigate('/cart');
  }, 300);
  const [toggleFavorite, togglingFavorite] = useDebounceAction(async () => {
    const nextValue = window.localStorage.getItem('liteshop.accessToken')
      ? await toggleServerFavoriteProduct(productId)
      : toggleFavoriteProduct(productId);
    setFavorite(nextValue);
    setFavoriteNotice(nextValue ? '已加入收藏' : '已取消收藏');
  }, 300);
  const moveImage = (offset: number): void => {
    setImageIndex((current) => (current + offset + detailSlides.length) % detailSlides.length);
  };
  const handleDrawerKeyDown = (event: ReactKeyboardEvent<HTMLElement>): void => {
    if (event.key !== 'Tab') return;
    const focusable = drawerRef.current?.querySelectorAll<HTMLElement>('button:not([disabled])');
    if (!focusable?.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };
  useEffect(() => {
    if (!skuOpen) return undefined;
    const previousFocus =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const closeOnEscape = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') setSkuOpen(false);
    };
    document.addEventListener('keydown', closeOnEscape);
    document.body.style.overflow = 'hidden';
    drawerRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', closeOnEscape);
      document.body.style.overflow = '';
      previousFocus?.focus();
    };
  }, [skuOpen]);
  if (query.isError)
    return (
      <main className="trade-page">
        <p className="feedback error-state">商品加载失败，请返回重试</p>
        <Link to="/">返回首页</Link>
      </main>
    );
  if (query.isLoading || !product)
    return (
      <main className="trade-page">
        <p className="feedback">商品加载中…</p>
      </main>
    );
  const skuName = selectedSku?.name ?? '请选择规格';
  return (
    <main className="trade-page">
      <Link className="back-link" to="/">
        ‹ 返回
      </Link>
      <div
        className={`detail-visual detail-visual-${imageIndex + 1}`}
        aria-label={`${product.name} 商品图轮播`}
        role="region"
        aria-roledescription="carousel"
      >
        <button
          className="visual-control visual-control-prev"
          type="button"
          onClick={() => moveImage(-1)}
          aria-label="上一张商品图"
        >
          ‹
        </button>
        <span aria-live="polite">{detailSlides[imageIndex]}</span>
        <button
          className="visual-control visual-control-next"
          type="button"
          onClick={() => moveImage(1)}
          aria-label="下一张商品图"
        >
          ›
        </button>
        <div className="hero-dots" role="tablist" aria-label="选择商品图片">
          {detailSlides.map((slide, index) => (
            <button
              className={index === imageIndex ? 'active' : ''}
              type="button"
              role="tab"
              aria-selected={index === imageIndex}
              aria-label={`查看${slide}`}
              key={slide}
              onClick={() => setImageIndex(index)}
            />
          ))}
        </div>
      </div>
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
      <section className="detail-section" aria-label="商品评价">
        <div className="section-title">
          <h2>用户评价</h2>
          <span>
            {reviewsQuery.data?.averageRating
              ? `${reviewsQuery.data.averageRating} 分`
              : '暂无评分'}
          </span>
        </div>
        {reviewsQuery.isLoading && <p className="muted">评价加载中…</p>}
        {reviewsQuery.isError && (
          <p className="feedback error-state" role="alert">
            评价加载失败，请稍后重试。
          </p>
        )}
        {!reviewsQuery.isLoading && !reviewsQuery.isError && !reviewsQuery.data?.items.length && (
          <p className="muted">暂无已审核评价</p>
        )}
        {reviewsQuery.data?.items.slice(0, 3).map((review) => (
          <article className="review-item" key={review.id}>
            <div aria-label={`${review.rating} 星评分`}>
              {'★'.repeat(review.rating)}
              {'☆'.repeat(5 - review.rating)}
            </div>
            <p>{review.content || '用户未填写文字评价'}</p>
            <time dateTime={review.createdAt}>
              {new Date(review.createdAt).toLocaleDateString('zh-CN')}
            </time>
          </article>
        ))}
      </section>
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
      {skuOpen && (
        <div className="drawer-backdrop" role="presentation" onClick={() => setSkuOpen(false)}>
          <aside
            ref={drawerRef}
            tabIndex={-1}
            className="sku-drawer"
            role="dialog"
            aria-modal="true"
            aria-labelledby="sku-title"
            onClick={(event) => event.stopPropagation()}
            onKeyDown={handleDrawerKeyDown}
          >
            <div className="drawer-grabber" />
            <div className="drawer-header">
              <h2 id="sku-title">选择规格</h2>
              <button className="drawer-close" type="button" onClick={() => setSkuOpen(false)}>
                关闭
              </button>
            </div>
            {product.skus.map((sku) => (
              <button
                type="button"
                className={`sku-option${sku.skuId === selectedSku?.skuId ? ' selected' : ''}`}
                key={sku.skuId}
                onClick={() => setSelectedSkuId(sku.skuId)}
              >
                {sku.name}
                <span>{formatPrice(sku.priceCents)}</span>
              </button>
            ))}
            <button
              className="primary-action"
              type="button"
              onClick={() => void addToCart()}
              disabled={loading || !selectedSku}
            >
              {loading ? '加入中…' : '确定'}
            </button>
          </aside>
        </div>
      )}
    </main>
  );
}
