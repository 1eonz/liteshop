import Link from 'next/link';

export default function NotFound(): JSX.Element {
  return (
    <main className="site-section">
      <div className="site-container site-container--reading">
        <p className="site-eyebrow">404</p>
        <h1>这页暂时走丢了</h1>
        <p className="site-lede">回到首页，继续探索 LiteShop 的产品能力。</p>
        <Link className="site-button" href="/">
          回到首页<span aria-hidden="true">↗</span>
        </Link>
      </div>
    </main>
  );
}
