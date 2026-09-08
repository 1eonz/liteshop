import { expect, test } from '@playwright/test';

test('SKU 抽屉支持键盘焦点循环、Escape 关闭和焦点回收', async ({ page }) => {
  await page.goto('/product/1');
  const trigger = page.getByRole('button', { name: /规格：/ });
  await trigger.focus();
  await page.keyboard.press('Enter');

  const dialog = page.getByRole('dialog', { name: '选择规格' });
  await expect(dialog).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', { name: '关闭' })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(dialog.getByRole('button', { name: '确定' })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(dialog.getByRole('button', { name: '关闭' })).toBeFocused();
  await page.keyboard.press('Escape');

  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
});

test('H5 在减少动态和 320px 视口下保持可用', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('/product/1');

  const transitionDuration = await page
    .locator('.detail-visual')
    .evaluate((element) => window.getComputedStyle(element).transitionDuration);
  expect(transitionDuration).toBe('0s');
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
  await expect(page.getByRole('button', { name: '加入购物车' })).toBeVisible();
});
