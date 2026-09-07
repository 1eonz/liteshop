import type { ApiEnvelope, DashboardData } from '@liteshop/shared-types';
import { httpClient } from '../http';

export interface ThemeSettings {
  primaryColor: string;
  navigationStyle: string;
  tabbarStyle: string;
}

/** 读取后台看板聚合数据。 */
export async function getDashboard(): Promise<DashboardData> {
  const response = await httpClient.get<ApiEnvelope<DashboardData>>('/admin/dashboard');
  return response.data.data;
}

/** 读取商城主题配置。 */
export async function getThemeSettings(): Promise<ThemeSettings> {
  const response = await httpClient.get<ApiEnvelope<ThemeSettings>>('/settings/theme');
  return response.data.data;
}

/** 更新商城主题配置。 */
export async function updateThemeSettings(input: ThemeSettings): Promise<ThemeSettings> {
  const response = await httpClient.put<ApiEnvelope<ThemeSettings>>('/settings/theme', input);
  return response.data.data;
}

/** 读取功能开关。 */
export async function listFeatureFlags(): Promise<Array<{ key: string; enabled: boolean }>> {
  const response =
    await httpClient.get<ApiEnvelope<{ items: Array<{ key: string; enabled: boolean }> }>>(
      '/settings/feature-flags',
    );
  return response.data.data.items;
}
