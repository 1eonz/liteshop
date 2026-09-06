import type { JSX } from 'react';
import type { StoreComponentSchema, StorePageSchema } from '@liteshop/shared-types';

interface SchemaRendererProps {
  schema: StorePageSchema;
}

function renderComponent(component: StoreComponentSchema): JSX.Element {
  switch (component.type) {
    case 'SearchBar':
      return (
        <div className="schema-search">{String(component.props.placeholder ?? '搜索商品')}</div>
      );
    case 'ActivityBanner':
    case 'ImageBanner':
      return <div className="schema-banner">{String(component.props.title ?? '活动专区')}</div>;
    case 'CategoryGrid':
      return <div className="schema-placeholder">热门分类</div>;
    case 'ProductGrid':
    case 'ProductList':
      return <div className="schema-placeholder">商品列表</div>;
    case 'Carousel':
      return <div className="schema-placeholder">精选轮播</div>;
    case 'Tabbar':
      return (
        <nav className="schema-tabbar" aria-label="页面导航">
          首页 / 分类 / 购物车 / 我的
        </nav>
      );
    case 'RichText':
      return <p className="schema-text">{String(component.props.text ?? '')}</p>;
    case 'Spacer':
      return <div aria-hidden="true" className="schema-spacer" />;
    default:
      return <div className="feedback">暂不支持此组件</div>;
  }
}

/** 根据版本化 Schema 渲染安全组件，未知组件降级为空态。 */
export function SchemaRenderer({ schema }: SchemaRendererProps): JSX.Element {
  return (
    <>
      {schema.components.map((component) => (
        <section key={component.id}>{renderComponent(component)}</section>
      ))}
    </>
  );
}
