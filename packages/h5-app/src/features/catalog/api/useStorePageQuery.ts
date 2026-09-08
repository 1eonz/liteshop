import { useQuery } from '@tanstack/react-query';
import type { StorePageSchema } from '@liteshop/shared-types';
import { getStoreHomePage } from '../../../service/pages';

/** 商城首页 Schema 查询，页面只负责编排渲染结果。 */
export function useStoreHomePageQuery() {
  return useQuery<StorePageSchema>({
    queryKey: ['store-page', 'home'],
    queryFn: getStoreHomePage,
  });
}
