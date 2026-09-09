import type { JSX } from 'react';

/** 首页专用骨架屏，保持搜索、轮播、分类和商品区的首屏几何尺寸稳定。 */
export function HomeSkeleton(): JSX.Element {
  return (
    <div className="home-skeleton" aria-busy="true" aria-label="首页加载中">
      <div className="home-skeleton__header">
        <span className="skeleton-block skeleton-block--brand" />
        <span className="skeleton-block skeleton-block--search" />
      </div>
      <span className="skeleton-block skeleton-block--hero" />
      <section className="home-skeleton__section" aria-hidden="true">
        <span className="skeleton-block skeleton-block--title" />
        <div className="home-skeleton__categories">
          {Array.from({ length: 8 }, (_, index) => (
            <span className="skeleton-block skeleton-block--category" key={index} />
          ))}
        </div>
      </section>
      <section className="home-skeleton__section" aria-hidden="true">
        <span className="skeleton-block skeleton-block--title" />
        <div className="home-skeleton__products">
          {Array.from({ length: 4 }, (_, index) => (
            <span className="skeleton-block skeleton-block--product" key={index} />
          ))}
        </div>
      </section>
    </div>
  );
}
