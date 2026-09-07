import { test, expect } from '@playwright/test';

test('后台联系表单可登录、筛选、查看并更新状态', async ({ page }) => {
  let status = 'NEW';
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        requestId: 'e2e-login',
        data: { accessToken: 'e2e-admin-token', refreshToken: 'e2e-refresh-token' },
      }),
    });
  });
  await page.route('**/api/v1/admin/dashboard', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        requestId: 'e2e-dashboard',
        data: {
          metrics: { salesAmount: 0, orderCount: 0, productCount: 0, pendingShipmentCount: 0 },
          trend: [],
          ranking: [],
        },
      }),
    });
  });
  await page.route('**/api/v1/admin/contact/forms/7', async (route) => {
    const payload = route.request().postDataJSON() as { status?: string };
    status = payload.status ?? status;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        requestId: 'e2e-contact',
        data: {
          id: 7,
          name: '林晓',
          email: 'lin@example.com',
          phone: '13800000000',
          company: '示例公司',
          message: '希望了解商品与订单模块。',
          status,
          source: 'site',
          createdAt: '2026-09-07T08:00:00+08:00',
          updatedAt: '2026-09-07T08:00:00+08:00',
        },
      }),
    });
  });
  await page.route('**/api/v1/admin/contact/forms', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        requestId: 'e2e-contact-list',
        data: {
          items: [
            {
              id: 7,
              name: '林晓',
              email: 'lin@example.com',
              phone: '13800000000',
              company: '示例公司',
              message: '希望了解商品与订单模块。',
              status,
              source: 'site',
              createdAt: '2026-09-07T08:00:00+08:00',
              updatedAt: '2026-09-07T08:00:00+08:00',
            },
          ],
        },
      }),
    });
  });

  await page.goto('http://127.0.0.1:5174/login');
  await page.getByLabel('手机号').fill('13800000000');
  await page.getByLabel('验证码').fill('123456');
  await page.getByRole('button', { name: '进入后台' }).click();
  await expect(page).toHaveURL('http://127.0.0.1:5174/');
  await page.getByRole('link', { name: '联系表单' }).click();
  await expect(page.getByRole('heading', { name: '联系表单' })).toBeVisible();
  await expect(page.getByText('林晓')).toBeVisible();
  await page.getByRole('button', { name: /林晓/ }).click();
  await expect(page.getByText('希望了解商品与订单模块。')).toBeVisible();
  const updateResponse = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT' && response.url().includes('/admin/contact/forms/7'),
  );
  await page.getByRole('button', { name: '跟进中' }).click();
  const response = await updateResponse;
  expect(response.status()).toBe(200);
});
