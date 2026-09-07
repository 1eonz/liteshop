import { expect, test } from '@playwright/test';

const envelope = (data: unknown) => ({
  code: 0,
  message: '',
  data,
  requestId: 'e2e-request',
});

test('H5 交易主链路可以从登录走到订单列表', async ({ page }) => {
  let created = false;
  await page.route('**/api/v1/auth/sms-code', async (route) => {
    await route.fulfill({ json: envelope({ sent: true }) });
  });
  await page.route('**/api/v1/auth/login', async (route) => {
    await route.fulfill({
      json: envelope({ accessToken: 'e2e-access-token', expiresIn: 7200, subject: '1' }),
    });
  });
  await page.route('**/api/v1/user/addresses', async (route) => {
    if (route.request().method() !== 'GET') return route.continue();
    await route.fulfill({
      json: envelope({
        items: [
          {
            id: 1,
            receiverName: '测试用户',
            phone: '13800000000',
            provinceCode: '110000',
            cityCode: '110100',
            districtCode: '110101',
            detail: '测试地址',
            isDefault: true,
            createdAt: '2026-01-01T00:00:00Z',
            updatedAt: '2026-01-01T00:00:00Z',
          },
        ],
      }),
    });
  });
  await page.route('**/api/v1/orders/freight-calc', async (route) => {
    await route.fulfill({ json: envelope({ freightAmount: 0 }) });
  });
  await page.route(/\/api\/v1\/orders(?:\?.*)?$/, async (route) => {
    // 列表和创建共用路径，按 HTTP 方法分流，避免路由注册顺序影响测试。
    if (route.request().method() === 'GET') {
      await route.fulfill({
        json: envelope({
          items: created
            ? [
                {
                  id: 101,
                  orderNo: 'LS-E2E-101',
                  status: 'PENDING_PAYMENT',
                  totalAmount: 12900,
                  productAmount: 12900,
                  freightAmount: 0,
                  discountAmount: 0,
                  createdAt: '2026-01-01T00:00:00Z',
                  items: [],
                },
              ]
            : [],
          meta: { page: 1, pageSize: 20, total: created ? 1 : 0, hasNext: false },
        }),
      });
      return;
    }
    created = true;
    await route.fulfill({
      json: envelope({
        id: 101,
        orderNo: 'LS-E2E-101',
        status: 'PENDING_PAYMENT',
        totalAmount: 12900,
        productAmount: 12900,
        freightAmount: 0,
        discountAmount: 0,
        createdAt: '2026-01-01T00:00:00Z',
        items: [],
      }),
    });
  });
  await page.route('**/api/v1/orders/101', async (route) => {
    await route.fulfill({
      json: envelope({
        id: 101,
        orderNo: 'LS-E2E-101',
        status: 'PENDING_PAYMENT',
        totalAmount: 12900,
        productAmount: 12900,
        freightAmount: 0,
        discountAmount: 0,
        createdAt: '2026-01-01T00:00:00Z',
        items: [],
      }),
    });
  });
  await page.route('**/api/v1/payments', async (route) => {
    await route.fulfill({
      json: envelope({
        id: 'PAY-E2E-101',
        orderId: 101,
        provider: 'WECHAT',
        amountCents: 12900,
        status: 'PENDING',
      }),
    });
  });
  await page.route('**/api/v1/cart/items', async (route) => {
    await route.fulfill({
      json: envelope({
        item: {
          id: 1,
          skuId: 1,
          skuCode: 'DEMO-1',
          name: '晨雾保温杯',
          priceCents: 12900,
          quantity: 1,
          specs: {},
          stale: false,
        },
      }),
    });
  });
  await page.route('**/api/v1/cart', async (route) => {
    await route.fulfill({
      json: envelope({
        items: [
          {
            id: 1,
            skuId: 1,
            skuCode: 'DEMO-1',
            name: '晨雾保温杯',
            priceCents: 12900,
            quantity: 1,
            specs: {},
            stale: false,
          },
        ],
      }),
    });
  });
  await page.route('**/api/v1/cart/items/**', async (route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ json: envelope({ removed: true }) });
      return;
    }
    await route.fulfill({ json: envelope({ item: {} }) });
  });

  await page.goto('/login');
  await page.getByPlaceholder('请输入手机号').fill('13800000000');
  await page.getByRole('button', { name: '获取验证码' }).click();
  await page.getByPlaceholder('6 位验证码').fill('123456');
  await page.getByRole('button', { name: '登录' }).click();
  await expect(page).toHaveURL(/\/me$/);

  await page.goto('/product/1');
  await Promise.all([
    page.waitForResponse((response) => response.url().endsWith('/cart/items')),
    page.getByRole('button', { name: '加入购物车' }).click(),
  ]);
  await page.evaluate(() => {
    window.history.pushState({}, '', '/cart');
    window.dispatchEvent(new PopStateEvent('popstate', { state: window.history.state }));
  });
  await expect(page.getByText('晨雾保温杯')).toBeVisible();
  await page.getByRole('button', { name: '去结算' }).click();
  await expect(page).toHaveURL(/\/order\/confirm$/);
  await page.getByRole('button', { name: '提交订单' }).click();
  await expect(page.getByRole('heading', { name: '订单已提交' })).toBeVisible();

  await page.goto('/payment/101');
  await page.getByRole('button', { name: '使用微信支付' }).click();
  await expect(page.getByText('支付单已创建')).toBeVisible();

  await page.goto('/orders');
  await expect(page.getByText('LS-E2E-101')).toBeVisible();
});
