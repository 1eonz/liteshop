import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { CategorySummary } from '@liteshop/shared-types';
import {
  createAdminCategory,
  deleteAdminCategory,
  listAdminCategories,
  updateAdminCategory,
} from '../../../service/admin/catalog';
import { isRecoverableApiError } from '../../../service/http';

/** 后台分类查询。 */
export function useAdminCategoriesQuery() {
  return useQuery<CategorySummary[]>({
    queryKey: ['admin-categories'],
    queryFn: async () => {
      try {
        return await listAdminCategories();
      } catch (error) {
        if (!isRecoverableApiError(error)) throw error;
        return [];
      }
    },
  });
}

/** 后台分类新增、编辑和停用动作。 */
export function useAdminCategoryMutations() {
  const queryClient = useQueryClient();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['admin-categories'] });
  };
  return {
    create: useMutation({ mutationFn: createAdminCategory, retry: 0, onSuccess: refresh }),
    update: useMutation({
      mutationFn: ({
        categoryId,
        input,
      }: {
        categoryId: number;
        input: Partial<CategorySummary>;
      }) => updateAdminCategory(categoryId, input),
      retry: 0,
      onSuccess: refresh,
    }),
    remove: useMutation({ mutationFn: deleteAdminCategory, retry: 0, onSuccess: refresh }),
  };
}
