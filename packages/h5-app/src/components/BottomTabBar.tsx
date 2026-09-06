import type { JSX } from 'react';
import { Link } from 'react-router-dom';

interface BottomTabBarProps {
  active?: 'home' | 'category' | 'cart' | 'me';
}

/** H5 底部导航，跨页面复用的 UI 放在 components 层。 */
export function BottomTabBar({ active = 'home' }: BottomTabBarProps): JSX.Element {
  const className = (key: BottomTabBarProps['active']): string => (active === key ? 'active' : '');
  return (
    <nav className="tabbar" aria-label="主导航">
      <Link className={className('home')} to="/">
        首页
      </Link>
      <Link className={className('category')} to="/categories">
        分类
      </Link>
      <Link className={className('cart')} to="/cart">
        购物车
      </Link>
      <Link className={className('me')} to="/me">
        我的
      </Link>
    </nav>
  );
}
