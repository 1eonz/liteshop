/**
 * 后台 API 兼容出口。
 *
 * 新代码应从 service/admin/<domain> 导入；保留本文件是为了兼容旧页面和外部包，
 * 避免一次领域拆分引发跨包破坏性变更。
 */
export * from './admin/access';
export * from './admin/catalog';
export * from './admin/contact';
export * from './admin/inventory';
export * from './admin/orders';
export * from './admin/settings';
