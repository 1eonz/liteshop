import { expect, test, type APIRequestContext } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE ?? 'http://127.0.0.1:8000/api/v1';

async function backendIsAvailable(request: APIRequestContext): Promise<boolean> {
  try {
    const response = await request.get(`${apiBase.replace('/api/v1', '')}/health`);
    return response.ok();
  } catch {
    return false;
  }
}

test.describe('真实后端接口联调', () => {
  test('商品分页和边界参数通过真实 HTTP API 返回', async ({ request }) => {
    test.skip(!(await backendIsAvailable(request)), '后端未启动，跳过真实接口联调');

    const response = await request.get(`${apiBase}/products?page=1&pageSize=1`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.code).toBe(0);
    expect(body.data.meta.page).toBe(1);
    expect(body.data.meta.pageSize).toBe(1);
    expect(body.data.items.length).toBeLessThanOrEqual(1);

    const invalid = await request.get(`${apiBase}/products?pageSize=101`);
    expect(invalid.status()).toBe(422);
  });

  test('不存在商品返回契约错误码且不回退演示数据', async ({ request }) => {
    test.skip(!(await backendIsAvailable(request)), '后端未启动，跳过真实接口联调');

    const response = await request.get(`${apiBase}/products/2147483647`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body.code).toBe(40401);
    expect(body.data).toBeUndefined();
  });

  test('H5 分类页由真实 API 响应驱动', async ({ page }) => {
    test.skip(!(await backendIsAvailable(await page.request)), '后端未启动，跳过真实页面联调');

    const productsResponse = page.waitForResponse(
      (response) => response.url().includes('/api/v1/products') && response.request().method() === 'GET',
    );
    await page.goto('/categories');
    const response = await productsResponse;
    expect(response.status()).toBe(200);
    await expect(page.getByRole('heading', { name: '商品分类' })).toBeVisible();
    await expect(page.getByRole('tab', { name: '全部' })).toBeVisible();
  });
});
