import type { JSX } from 'react';
import { Link } from 'react-router-dom';

interface BottomTabBarProps {
  active?: 'home' | 'category' | 'cart' | 'me';
  items?: readonly TabBarItem[];
}

export interface TabBarItem {
  key: 'home' | 'category' | 'cart' | 'me';
  label: string;
  to: string;
}

const DEFAULT_ITEMS: readonly TabBarItem[] = [
  { key: 'home', label: '首页', to: '/' },
  { key: 'category', label: '分类', to: '/categories' },
  { key: 'cart', label: '购物车', to: '/cart' },
  { key: 'me', label: '我的', to: '/me' },
];

/** H5 底部导航，跨页面复用的 UI 放在 components 层。 */
export function BottomTabBar({
  active = 'home',
  items = DEFAULT_ITEMS,
}: BottomTabBarProps): JSX.Element {
  const className = (key: TabBarItem['key']): string => (active === key ? 'active' : '');
  return (
    <nav className="tabbar" aria-label="主导航">
      {items.map((item) => (
        <Link className={className(item.key)} to={item.to} key={item.key}>
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
