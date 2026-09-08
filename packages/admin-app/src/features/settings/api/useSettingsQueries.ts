/** 设置领域查询和写操作由 service 层提供，页面通过此出口接入。 */
export {
  getThemeSettings,
  listFeatureFlags,
  updateThemeSettings,
} from '../../../service/admin/settings';
