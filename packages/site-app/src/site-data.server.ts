import type { SitePageSchema } from './site-data';
import { getSitePage, sitePages } from './site-data';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8000/api/v1';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isSitePage(value: unknown): value is SitePageSchema {
  if (!isRecord(value)) return false;
  return (
    typeof value.slug === 'string' &&
    typeof value.title === 'string' &&
    typeof value.description === 'string' &&
    isRecord(value.seo) &&
    Array.isArray(value.components)
  );
}

function normalizeSitePage(value: SitePageSchema): SitePageSchema {
  const seo: SitePageSchema['seo'] = {
    title: value.seo?.title || value.title,
    description: value.seo?.description || value.description,
    keywords: Array.isArray(value.seo?.keywords) ? value.seo.keywords : [],
    noIndex: value.seo?.noIndex,
  };
  return { ...value, seo };
}

function unwrapPage(value: unknown): SitePageSchema | null {
  if (!isRecord(value)) return null;
  const data = value.data;
  return isSitePage(data) ? data : isSitePage(value) ? value : null;
}

/**
 * 读取官网发布页面。后台接口不可达或响应不符合契约时，回退到已审核的本地 Schema。
 * Next 的标签缓存允许后台通过 revalidate Route Handler 精确失效单页缓存。
 */
export async function loadSitePage(slug: string): Promise<SitePageSchema | null> {
  const fallback = getSitePage(slug);
  try {
    const response = await fetch(
      `${API_BASE.replace(/\/$/, '')}/site/pages/${encodeURIComponent(slug)}`,
      {
        next: { revalidate: 60, tags: [`site-page:${slug}`] },
      },
    );
    if (!response.ok) return fallback;
    const page = unwrapPage((await response.json()) as unknown);
    return page ? applySiteChrome(normalizeSitePage(page)) : fallback;
  } catch {
    return fallback;
  }
}

/** 读取官网页面 slug 列表，构建失败时使用已审核的本地页面。 */
export async function loadSitePageSlugs(): Promise<string[]> {
  const fallback = Object.keys(sitePages);
  try {
    const response = await fetch(`${API_BASE.replace(/\/$/, '')}/site/pages`, {
      next: { revalidate: 60, tags: ['site-pages'] },
    });
    if (!response.ok) return fallback;
    const payload: unknown = await response.json();
    if (!isRecord(payload) || !isRecord(payload.data) || !Array.isArray(payload.data.items))
      return fallback;
    const slugs = payload.data.items.flatMap((item): string[] => {
      if (!isRecord(item) || typeof item.slug !== 'string' || !/^[a-z0-9-]+$/.test(item.slug))
        return [];
      return [item.slug];
    });
    return slugs.length ? slugs : fallback;
  } catch {
    return fallback;
  }
}

interface NavigationItem {
  label: string;
  href: string;
  openNewTab?: boolean;
}

interface SiteSettings {
  siteName?: string;
  logoUrl?: string;
  defaultTitle?: string;
  defaultDescription?: string;
}

function parseNavigation(value: unknown): NavigationItem[] {
  if (!isRecord(value) || !isRecord(value.data) || !Array.isArray(value.data.items)) return [];
  return value.data.items.flatMap((item): NavigationItem[] => {
    if (!isRecord(item) || typeof item.label !== 'string' || typeof item.href !== 'string')
      return [];
    return [
      {
        label: item.label,
        href: item.href,
        openNewTab: item.openNewTab === true,
      },
    ];
  });
}

function parseSettings(value: unknown): SiteSettings {
  if (!isRecord(value) || !isRecord(value.data)) return {};
  const data = value.data;
  return {
    siteName: typeof data.siteName === 'string' ? data.siteName : undefined,
    logoUrl: typeof data.logoUrl === 'string' ? data.logoUrl : undefined,
    defaultTitle: typeof data.defaultTitle === 'string' ? data.defaultTitle : undefined,
    defaultDescription:
      typeof data.defaultDescription === 'string' ? data.defaultDescription : undefined,
  };
}

/** 将后台导航和官网设置注入页面 Schema，保持本地页面作为安全回退。 */
async function applySiteChrome(page: SitePageSchema): Promise<SitePageSchema> {
  try {
    const [settingsResponse, headerResponse, footerResponse] = await Promise.all([
      fetch(`${API_BASE.replace(/\/$/, '')}/settings/site`, {
        next: { revalidate: 60, tags: ['site-settings'] },
      }),
      fetch(`${API_BASE.replace(/\/$/, '')}/site/navigation?location=header`, {
        next: { revalidate: 60, tags: ['site-navigation:header'] },
      }),
      fetch(`${API_BASE.replace(/\/$/, '')}/site/navigation?location=footer`, {
        next: { revalidate: 60, tags: ['site-navigation:footer'] },
      }),
    ]);
    const settings = settingsResponse.ok ? parseSettings(await settingsResponse.json()) : {};
    const header = headerResponse.ok ? parseNavigation(await headerResponse.json()) : [];
    const footer = footerResponse.ok ? parseNavigation(await footerResponse.json()) : [];
    const components = page.components.map((component) => {
      if (component.type === 'Navbar' && header.length) {
        return {
          ...component,
          props: {
            ...component.props,
            links: header,
            brandName: settings.siteName,
            logoUrl: settings.logoUrl,
          },
        };
      }
      if (component.type === 'Footer' && footer.length) {
        return {
          ...component,
          props: {
            ...component.props,
            groups: [{ title: '导航', links: footer }],
          },
        };
      }
      return component;
    });
    return {
      ...page,
      title: page.title || settings.defaultTitle || page.title,
      description: page.description || settings.defaultDescription || page.description,
      components,
    };
  } catch {
    return page;
  }
}
