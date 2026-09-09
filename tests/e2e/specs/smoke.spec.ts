import { test, expect } from '@playwright/test';

test('H5 首页能显示品牌和商品区', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('LiteShop')).toBeVisible();
  await expect(page.getByText('人气好物')).toBeVisible();
});

test('商品详情路径可打开', async ({ page }) => {
  await page.goto('/product/1');
  await expect(page.getByText('晨雾保温杯')).toBeVisible();
});

test('搭建器草稿预览可渲染 Schema 组件', async ({ page }) => {
  const schema = encodeURIComponent(
    JSON.stringify({
      id: 99,
      slug: 'preview',
      version: 1,
      components: [
        { id: 'announcement-1', type: 'AnnouncementBar', props: { text: '预览公告' }, style: {} },
        { id: 'product-1', type: 'ProductGrid', props: { title: '预览商品' }, style: {} },
      ],
    }),
  );
  await page.goto(`/preview?schema=${schema}`);
  await expect(page.getByText('预览公告')).toBeVisible();
  await expect(page.getByText('商品列表')).toBeVisible();
});

test('H5 首页消费后台发布的 Schema，而不是仅渲染本地预览', async ({ page }) => {
  await page.route('**/api/v1/pages/1/schema', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        requestId: 'e2e-schema',
        data: {
          id: 1,
          slug: 'home',
          channel: 'store',
          status: 'PUBLISHED',
          version: 1,
          isHome: true,
          components: [
            {
              id: 'announcement-e2e',
              type: 'AnnouncementBar',
              props: { label: '发布验证', text: '来自后台发布的首页 Schema' },
              style: {},
            },
          ],
        },
      }),
    });
  });

  await page.goto('/');
  await expect(page.getByText('来自后台发布的首页 Schema')).toBeVisible();
  await expect(page.getByText('LiteShop')).not.toBeVisible();
});
