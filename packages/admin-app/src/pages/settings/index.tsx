import type { JSX } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { getThemeSettings, listFeatureFlags, updateThemeSettings } from '../../service/admin';
import { useDebounceAction } from '../../hooks';

interface LocalSettings {
  shopName: string;
  timeoutMinutes: number;
  paymentSandbox: boolean;
  primaryColor: string;
  navigationStyle: string;
  tabbarStyle: string;
}

const DEFAULT_PRIMARY_COLOR = 'var(--color-primary-500)';

function resolvePrimaryColor(value: string): string {
  if (!value.startsWith('var(')) return value;
  return getComputedStyle(document.documentElement).getPropertyValue('--color-primary-500').trim();
}

function readSettings(): LocalSettings {
  try {
    const raw = window.localStorage.getItem('liteshop.admin.settings');
    if (raw)
      return {
        ...{
          shopName: 'LiteShop',
          timeoutMinutes: 30,
          paymentSandbox: true,
          primaryColor: DEFAULT_PRIMARY_COLOR,
          navigationStyle: 'glass',
          tabbarStyle: 'gallery',
        },
        ...(JSON.parse(raw) as Partial<LocalSettings>),
      };
  } catch {
    /* 首次访问或旧值损坏时使用默认设置 */
  }
  return {
    shopName: 'LiteShop',
    timeoutMinutes: 30,
    paymentSandbox: true,
    primaryColor: DEFAULT_PRIMARY_COLOR,
    navigationStyle: 'glass',
    tabbarStyle: 'gallery',
  };
}

/** 系统设置页面，使用本地持久化保留开发环境配置，后端 settings API 就绪后可无缝替换 service。 */
export function SettingsPage(): JSX.Element {
  const [settings, setSettings] = useState<LocalSettings>(readSettings);
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState('');
  const themeQuery = useQuery({
    queryKey: ['theme-settings'],
    queryFn: getThemeSettings,
  });
  const flagsQuery = useQuery({
    queryKey: ['feature-flags'],
    queryFn: listFeatureFlags,
  });
  const themeMutation = useMutation({
    mutationFn: updateThemeSettings,
    retry: 0,
  });
  useEffect(() => {
    if (!themeQuery.data) return;
    setSettings((current) => ({ ...current, ...themeQuery.data }));
  }, [themeQuery.data]);
  const saveSettings = useCallback(async () => {
    setSaveError('');
    try {
      const primaryColor = resolvePrimaryColor(settings.primaryColor);
      if (!/^#[0-9a-fA-F]{6}$/.test(primaryColor)) {
        throw new Error('主题主色必须使用设计令牌中的六位颜色值。');
      }
      const savedTheme = await themeMutation.mutateAsync({
        primaryColor,
        navigationStyle: settings.navigationStyle,
        tabbarStyle: settings.tabbarStyle,
      });
      setSettings((current) => ({ ...current, ...savedTheme }));
      window.localStorage.setItem(
        'liteshop.admin.settings',
        JSON.stringify({ ...settings, ...savedTheme }),
      );
      setSaved(true);
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : '设置保存失败，请重试。');
      setSaved(false);
    }
  }, [settings, themeMutation]);
  const [save, saving] = useDebounceAction(saveSettings, 500);
  return (
    <div className="editor-page">
      <header>
        <div>
          <p>系统设置</p>
          <h1>基础设置</h1>
        </div>
        <button type="button" disabled={saving} onClick={() => void save()}>
          {saving ? '保存中…' : '保存设置'}
        </button>
      </header>
      <section className="editor-form">
        <label>
          商城名称
          <input
            value={settings.shopName}
            onChange={(event) => {
              setSaved(false);
              setSettings((current) => ({
                ...current,
                shopName: event.target.value,
              }));
            }}
          />
        </label>
        <label>
          订单超时取消（分钟）
          <input
            type="number"
            min="1"
            max="1440"
            value={settings.timeoutMinutes}
            onChange={(event) => {
              setSaved(false);
              setSettings((current) => ({
                ...current,
                timeoutMinutes: Number(event.target.value),
              }));
            }}
          />
        </label>
        <label>
          主题主色
          <input
            value={settings.primaryColor}
            onChange={(event) => {
              setSaved(false);
              setSettings((current) => ({
                ...current,
                primaryColor: event.target.value,
              }));
            }}
          />
        </label>
        <div className="form-grid">
          <label>
            导航样式
            <select
              value={settings.navigationStyle}
              onChange={(event) =>
                setSettings((current) => ({
                  ...current,
                  navigationStyle: event.target.value,
                }))
              }
            >
              <option value="glass">毛玻璃</option>
              <option value="solid">纯色</option>
            </select>
          </label>
          <label>
            Tabbar 样式
            <select
              value={settings.tabbarStyle}
              onChange={(event) =>
                setSettings((current) => ({
                  ...current,
                  tabbarStyle: event.target.value,
                }))
              }
            >
              <option value="gallery">画廊</option>
              <option value="minimal">极简</option>
            </select>
          </label>
        </div>
        <label className="check-row">
          <input
            type="checkbox"
            checked={settings.paymentSandbox}
            onChange={(event) => {
              setSaved(false);
              setSettings((current) => ({
                ...current,
                paymentSandbox: event.target.checked,
              }));
            }}
          />{' '}
          开启支付沙箱
        </label>
        <section className="settings-flags">
          <div className="panel-title">
            <h2>功能开关</h2>
            <span>{flagsQuery.isLoading ? '读取中…' : '服务端状态'}</span>
          </div>
          {flagsQuery.data?.map((flag) => (
            <div className="summary-row" key={flag.key}>
              <span>{flag.key}</span>
              <strong>{flag.enabled ? '已开启' : '已关闭'}</strong>
            </div>
          )) ?? <p className="muted">当前 API 不可用，使用本地开发配置。</p>}
        </section>
        {saved && (
          <p className="success-message" role="status">
            设置已保存到当前浏览器与主题接口
          </p>
        )}
        {saveError && (
          <p className="feedback error-state" role="alert">
            {saveError}
          </p>
        )}
      </section>
    </div>
  );
}
