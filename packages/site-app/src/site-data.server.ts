import type { SitePageSchema } from './site-data';
import { getSitePage } from './site-data';

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
    const response = await fetch(`${API_BASE.replace(/\/$/, '')}/site/pages/${encodeURIComponent(slug)}`, {
      next: { revalidate: 60, tags: [`site-page:${slug}`] },
    });
    if (!response.ok) return fallback;
    const page = unwrapPage((await response.json()) as unknown);
    return page ?? fallback;
  } catch {
    return fallback;
  }
}
