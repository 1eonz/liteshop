import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useQuery } from '@tanstack/react-query';
import { listCategories, listProducts } from '../../../service/products';
import { isRecoverableApiError } from '../../../service/http';
import { useCategoriesQuery } from './useCategoriesQuery';
import { useProductsQuery } from './useProductsQuery';

vi.mock('@tanstack/react-query', () => ({ useQuery: vi.fn() }));
vi.mock('../../../service/products', () => ({ listCategories: vi.fn(), listProducts: vi.fn() }));
vi.mock('../../../service/http', () => ({ isRecoverableApiError: vi.fn() }));

async function runQuery(): Promise<unknown> {
  const options = vi.mocked(useQuery).mock.calls.at(-1)?.[0];
  if (!options || typeof options.queryFn !== 'function') throw new Error('Missing query function');
  return options.queryFn({} as Parameters<typeof options.queryFn>[0]);
}

describe('商品查询的真实数据与演示回退边界', () => {
  beforeEach(() => vi.clearAllMocks());

  it('成功的空分类保持空数组，不伪造分类', async () => {
    vi.mocked(listCategories).mockResolvedValue([]);
    useCategoriesQuery();
    expect(await runQuery()).toEqual([]);
    expect(isRecoverableApiError).not.toHaveBeenCalled();
  });

  it('不以演示分类掩盖权限或业务失败', async () => {
    const error = new Error('Forbidden');
    vi.mocked(listCategories).mockRejectedValue(error);
    vi.mocked(isRecoverableApiError).mockReturnValue(false);
    useCategoriesQuery();
    await expect(runQuery()).rejects.toBe(error);
  });

  it('演示商品分页返回对应页面，尾页之后为空', async () => {
    vi.mocked(listProducts).mockRejectedValue(new Error('Offline'));
    vi.mocked(isRecoverableApiError).mockReturnValue(true);
    useProductsQuery({ page: 2, pageSize: 2 });
    expect(await runQuery()).toMatchObject({ items: [{ id: 3 }, { id: 4 }], meta: { total: 4, hasNext: false } });
    useProductsQuery({ page: 3, pageSize: 2 });
    expect(await runQuery()).toMatchObject({ items: [], meta: { total: 4, hasNext: false } });
  });

  it('生产或权限失败不回退演示商品', async () => {
    const error = new Error('Unauthorized');
    vi.mocked(listProducts).mockRejectedValue(error);
    vi.mocked(isRecoverableApiError).mockReturnValue(false);
    useProductsQuery();
    await expect(runQuery()).rejects.toBe(error);
  });
});
