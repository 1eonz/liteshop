export { httpClient } from './http';
export { loginAdmin } from './auth';
export type { AdminLoginInput, AdminLoginResult } from '@liteshop/shared-types';
export { listProducts } from './products';
export type { ProductListQuery } from '@liteshop/shared-types';
export {
  adjustInventory,
  getAdminProduct,
  getDashboard,
  listAdminOrders,
  listAdminProducts,
  listFreightTemplates,
  listInventory,
  shipAdminOrder,
  updateAdminProduct,
} from './admin';
export type {
  AdminProductQuery,
  ProductCreateInput,
  ProductSkuCreateInput,
  ProductUpdateInput,
  ShipOrderInput,
} from '@liteshop/shared-types';
