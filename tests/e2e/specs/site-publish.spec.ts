import { expect, test } from '@playwright/test';

test('官网发布缓存失效入口鉴权后可刷新并访问发布页', async ({ page, request }) => {
  const denied = await request.post('http://127.0.0.1:5175/api/revalidate', {
    data: { slug: 'about' },
  });
  expect(denied.status()).toBe(401);

  const accepted = await request.post('http://127.0.0.1:5175/api/revalidate', {
    headers: { 'x-revalidate-token': 'e2e-revalidate-token' },
    data: { slug: 'about', tags: ['site-pages', 'site-settings'] },
  });
  expect(accepted.status()).toBe(200);
  await expect(accepted.json()).resolves.toMatchObject({ revalidated: true, slug: 'about' });

  await page.goto('http://127.0.0.1:5175/about');
  await expect(
    page.getByRole('heading', { name: '系统应该让人更从容，而不是更忙碌' }),
  ).toBeVisible();
  await expect(page).toHaveTitle(/关于 LiteShop/);
});
