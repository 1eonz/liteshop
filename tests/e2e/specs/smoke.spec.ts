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
