import { afterEach, describe, expect, it, vi } from 'vitest';
import { loadSitePage, loadSitePageSlugs } from './site-data.server';

function response(data: unknown): Response {
  return new Response(JSON.stringify({ data }), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('官网动态数据读取', () => {
  it('读取后台页面并注入设置和导航', async () => {
    const page = {
      id: 8,
      slug: 'launch',
      title: '发布页',
      description: '发布说明',
      seo: { title: '', description: '', keywords: [] },
      components: [
        { id: 'nav', type: 'Navbar', props: { links: [] } },
        { id: 'footer', type: 'Footer', props: { groups: [] } },
      ],
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.endsWith('/site/pages/launch')) return response(page);
        if (url.endsWith('/settings/site'))
          return response({ siteName: '新 LiteShop', logoUrl: '/logo.svg' });
        if (url.includes('/site/navigation?location=header')) {
          return response({ items: [{ label: '发布页', href: '/launch' }] });
        }
        if (url.includes('/site/navigation?location=footer')) {
          return response({ items: [{ label: '帮助', href: '/help' }] });
        }
        return new Response(null, { status: 404 });
      }),
    );

    const loaded = await loadSitePage('launch');
    expect(loaded?.components[0]?.props).toMatchObject({
      brandName: '新 LiteShop',
      logoUrl: '/logo.svg',
    });
    expect(loaded?.components[1]?.props).toMatchObject({ groups: [{ title: '导航' }] });
  });

  it('后台不可用时回退到已审核页面 slug', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(null, { status: 503 })),
    );
    const slugs = await loadSitePageSlugs();
    expect(slugs).toContain('home');
  });
});
