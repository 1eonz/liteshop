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
