import type { JSX } from 'react';
import { useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { StoreComponentSchema, StorePageSchema, StoreComponentType } from '@liteshop/shared-types';
import { SchemaRenderer } from '../../components/SchemaRenderer';

const COMPONENT_TYPES = new Set<StoreComponentType>([
  'SearchBar',
  'Carousel',
  'CategoryGrid',
  'ProductGrid',
  'ActivityBanner',
  'Tabbar',
  'RichText',
  'ImageBanner',
  'Spacer',
  'ProductList',
  'ProductCarousel',
  'CouponBlock',
  'AnnouncementBar',
]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function parseSchema(raw: string | null): StorePageSchema | null {
  if (!raw) return null;
  try {
    const parsed: unknown = JSON.parse(raw);
    if (!isRecord(parsed) || !Array.isArray(parsed.components)) return null;
    const components = parsed.components.flatMap((value): StoreComponentSchema[] => {
      if (!isRecord(value) || typeof value.id !== 'string' || typeof value.type !== 'string') return [];
      if (!COMPONENT_TYPES.has(value.type as StoreComponentType)) return [];
      const props = isRecord(value.props) ? value.props : {};
      const style = isRecord(value.style)
        ? Object.fromEntries(
            Object.entries(value.style).filter((entry): entry is [string, string] => typeof entry[1] === 'string'),
          )
        : {};
      return [{ id: value.id, type: value.type as StoreComponentType, props, style }];
    });
    return {
      id: typeof parsed.id === 'number' ? parsed.id : 0,
      slug: typeof parsed.slug === 'string' ? parsed.slug : 'preview',
      name: typeof parsed.name === 'string' ? parsed.name : '页面预览',
      title: typeof parsed.title === 'string' ? parsed.title : '页面预览',
      version: typeof parsed.version === 'number' ? parsed.version : 1,
      isHome: parsed.isHome === true,
      components,
    };
  } catch {
    return null;
  }
}

/** 搭建器草稿预览页，只接受经过 Schema 白名单过滤的组件。 */
export function PreviewPage(): JSX.Element {
  const [searchParams] = useSearchParams();
  const schema = useMemo(() => parseSchema(searchParams.get('schema')), [searchParams]);
  return (
    <main className="h5-shell schema-preview-shell">
      <header className="schema-preview-header">
        <Link className="back-link" to="/">
          返回商城
        </Link>
        <strong>草稿预览</strong>
      </header>
      {schema ? (
        <SchemaRenderer schema={schema} />
      ) : (
        <section className="empty-state" aria-live="polite">
          <h1>预览内容不可用</h1>
          <p>请从后台搭建器重新打开预览。</p>
          <Link className="primary-action" to="/">
            返回首页
          </Link>
        </section>
      )}
    </main>
  );
}
