/** 商品领域查询出口，避免页面直接依赖聚合 Hook 文件。 */
export {
  useAdminProductQuery,
  useAdminProductsQuery,
  useCreateAdminProductMutation,
  useUpdateAdminProductMutation,
} from '../../../hooks/useAdminQueries';
