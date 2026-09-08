import { useQuery } from '@tanstack/react-query';
import type { CategorySummary } from '@liteshop/shared-types';
import { isRecoverableApiError } from '../../../service/http';
import { listCategories } from '../../../service/products';

const fallbackCategories: CategorySummary[] = [
  { id: 1, parentId: null, name: '新品', icon: '', sortOrder: 1 },
  { id: 2, parentId: null, name: '家居', icon: '', sortOrder: 2 },
  { id: 3, parentId: null, name: '服饰', icon: '', sortOrder: 3 },
  { id: 4, parentId: null, name: '数码', icon: '', sortOrder: 4 },
  { id: 5, parentId: null, name: '美妆', icon: '', sortOrder: 5 },
  { id: 6, parentId: null, name: '食品', icon: '', sortOrder: 6 },
  { id: 7, parentId: null, name: '运动', icon: '', sortOrder: 7 },
  { id: 8, parentId: null, name: '礼物', icon: '', sortOrder: 8 },
];

/** 商品分类查询，服务不可用时仅在开发环境提供安全的静态分类。 */
export function useCategoriesQuery() {
  return useQuery({
    queryKey: ['categories'],
    queryFn: async () => {
      try {
        const items = await listCategories();
        return items.length ? items : fallbackCategories;
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return fallbackCategories;
      }
    },
  });
}
