import { expect, test } from '@playwright/test';

const apiBase = process.env.E2E_API_BASE ?? 'http://127.0.0.1:8000/api/v1';

test.describe('真实后端接口联调', () => {
  test('商品分页和边界参数通过真实 HTTP API 返回', async ({ request }) => {
    const health = await request.get(`${apiBase.replace('/api/v1', '')}/health`);
    test.skip(!health.ok(), '后端未启动，跳过真实接口联调');

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
    const health = await request.get(`${apiBase.replace('/api/v1', '')}/health`);
    test.skip(!health.ok(), '后端未启动，跳过真实接口联调');

    const response = await request.get(`${apiBase}/products/2147483647`);
    expect(response.status()).toBe(404);
    const body = await response.json();
    expect(body.code).toBe(40401);
    expect(body.data).toBeUndefined();
  });
});
