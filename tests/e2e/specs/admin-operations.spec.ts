import { expect, test, type Page } from '@playwright/test';

const envelope = (data: unknown) => ({
  code: 0,
  message: 'ok',
  requestId: 'e2e-admin-operation',
  data,
});

async function authenticateAdmin(page: Page): Promise<void> {
  await page.addInitScript(() => {
    window.localStorage.setItem('liteshop.admin.accessToken', 'e2e-admin-token');
  });
}

test('RBAC 页面明确显示权限拒绝，不把 403 伪装为空列表', async ({ page }) => {
  await authenticateAdmin(page);
  await page.route('**/api/v1/admin/audit-logs', (route) =>
    route.fulfill({ json: envelope({ items: [] }) }),
  );
  for (const path of ['roles', 'permissions', 'users']) {
    await page.route(`**/api/v1/admin/${path}`, (route) =>
      route.fulfill({
        status: 403,
        json: { code: 40301, message: 'forbidden', requestId: 'e2e-denied', data: null },
      }),
    );
  }

  await page.goto('http://127.0.0.1:5174/audit');

  await expect(page.getByRole('alert').filter({ hasText: '权限数据加载失败' })).toBeVisible();
});

test('RBAC 编辑支持键盘操作并显示服务端冲突', async ({ page }) => {
  await authenticateAdmin(page);
  await page.route('**/api/v1/admin/audit-logs', (route) =>
    route.fulfill({ json: envelope({ items: [] }) }),
  );
  await page.route('**/api/v1/admin/permissions', (route) =>
    route.fulfill({ json: envelope({ items: [{ id: 1, code: 'rbac.write' }] }) }),
  );
  await page.route('**/api/v1/admin/users', (route) =>
    route.fulfill({
      json: envelope({
        items: [{ id: 9, nickname: '管理员', phone: '13800000000', roleIds: [1] }],
      }),
    }),
  );
  await page.route('**/api/v1/admin/roles/1', (route) =>
    route.fulfill({
      status: 409,
      json: { code: 40901, message: 'role conflict', requestId: 'e2e-conflict', data: null },
    }),
  );
  await page.route('**/api/v1/admin/roles', (route) =>
    route.fulfill({
      json: envelope({ items: [{ id: 1, name: '超级管理员', permissions: ['rbac.write'] }] }),
    }),
  );

  await page.goto('http://127.0.0.1:5174/audit');
  const manager = page.locator('section[aria-label="角色管理"]');
  const editButton = manager.getByRole('button', { name: '编辑' });
  await editButton.focus();
  await page.keyboard.press('Enter');
  await expect(manager.getByLabel('角色名称')).toHaveValue('超级管理员');
  await manager.getByLabel('角色名称').fill('受限管理员');

  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT' && response.url().endsWith('/admin/roles/1'),
  );
  await manager.getByRole('button', { name: '保存角色' }).press('Enter');
  expect((await responsePromise).status()).toBe(409);
  await expect(page.getByRole('status')).toContainText('角色保存失败');
});

test('运费模板一次提交多个地区计费项', async ({ page }) => {
  await authenticateAdmin(page);
  const template = {
    id: 1,
    name: '华东模板',
    type: 'PIECE',
    isDefault: false,
    enabled: true,
    items: [
      {
        id: 11,
        regionCodes: ['310000'],
        firstUnit: '1',
        firstFee: 800,
        additionalUnit: '1',
        additionalFee: 200,
        freeCondition: null,
      },
    ],
    createdAt: '2026-09-08T08:00:00+08:00',
    updatedAt: '2026-09-08T08:00:00+08:00',
  };
  let savedPayload: unknown = null;
  await page.route('**/api/v1/admin/freight-templates/1', async (route) => {
    savedPayload = route.request().postDataJSON();
    const input = savedPayload as {
      name: string;
      items: Array<{
        regionCodes: string[];
        firstUnit: number;
        firstFee: number;
        additionalUnit: number;
        additionalFee: number;
      }>;
    };
    await route.fulfill({
      json: envelope({
        ...template,
        name: input.name,
        items: input.items.map((item, index) => ({
          ...item,
          id: 11 + index,
          firstUnit: String(item.firstUnit),
          additionalUnit: String(item.additionalUnit),
          freeCondition: null,
        })),
      }),
    });
  });
  await page.route('**/api/v1/admin/freight-templates', (route) =>
    route.fulfill({ json: envelope({ items: [template] }) }),
  );

  await page.goto('http://127.0.0.1:5174/freight-templates');
  await page
    .locator('section[aria-label="运费模板列表"]')
    .getByRole('button', { name: '编辑' })
    .click();
  const editor = page.locator('section[aria-label="编辑运费模板"]');
  await editor.getByRole('button', { name: '新增计费项' }).click();
  await editor
    .getByLabel(/地区编码/)
    .nth(1)
    .fill('330000');
  await editor.getByLabel('首段费用（分）').nth(1).fill('900');
  await editor.getByLabel('续段费用（分）').nth(1).fill('250');

  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT' &&
      response.url().endsWith('/admin/freight-templates/1'),
  );
  await editor.getByRole('button', { name: '保存修改' }).click();
  expect((await responsePromise).status()).toBe(200);

  expect(savedPayload).toMatchObject({
    name: '华东模板',
    items: [
      { regionCodes: ['310000'], firstFee: 800, additionalFee: 200 },
      { regionCodes: ['330000'], firstFee: 900, additionalFee: 250 },
    ],
  });
});

test('已通过评价可以保存商家回复', async ({ page }) => {
  await authenticateAdmin(page);
  const review = {
    id: 5,
    productId: 1,
    skuId: 11,
    userId: 9,
    rating: 5,
    content: '包装完整，保温效果很好。',
    images: [],
    status: 'APPROVED',
    reason: null,
    merchantReply: null,
    merchantRepliedAt: null,
    createdAt: '2026-09-08T08:00:00+08:00',
  };
  let replyPayload: unknown = null;
  await page.route('**/api/v1/admin/reviews/5/reply', async (route) => {
    replyPayload = route.request().postDataJSON();
    await route.fulfill({
      json: envelope({
        id: 5,
        merchantReply: '感谢认可，我们会继续做好产品。',
        merchantRepliedAt: '2026-09-08T09:00:00+08:00',
      }),
    });
  });
  await page.route('**/api/v1/admin/reviews', (route) =>
    route.fulfill({ json: envelope({ items: [review] }) }),
  );

  await page.goto('http://127.0.0.1:5174/reviews');
  await page.getByRole('button', { name: /包装完整/ }).click();
  await page.getByLabel('商家回复').fill('感谢认可，我们会继续做好产品。');
  const responsePromise = page.waitForResponse(
    (response) =>
      response.request().method() === 'PUT' && response.url().endsWith('/admin/reviews/5/reply'),
  );
  await page.getByRole('button', { name: '保存回复' }).click();
  expect((await responsePromise).status()).toBe(200);
  expect(replyPayload).toEqual({ reply: '感谢认可，我们会继续做好产品。' });
  await expect(page.getByRole('status')).toContainText('商家回复已保存');
});
