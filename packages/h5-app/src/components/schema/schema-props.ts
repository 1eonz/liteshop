import type { StoreComponentSchema } from '@liteshop/shared-types';

/** 读取 Schema 字符串属性，非法值回退到默认值。 */
export function textProp(component: StoreComponentSchema, key: string, fallback = ''): string {
  const value = component.props[key];
  return typeof value === 'string' ? value : fallback;
}

/** 读取 Schema 数值属性，非法值回退到默认值。 */
export function numberProp(component: StoreComponentSchema, key: string, fallback: number): number {
  const value = component.props[key];
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/** 读取 Schema 布尔属性，非法值回退到默认值。 */
export function booleanProp(
  component: StoreComponentSchema,
  key: string,
  fallback: boolean,
): boolean {
  const value = component.props[key];
  return typeof value === 'boolean' ? value : fallback;
}

/** 仅允许站内绝对路径，避免 Schema 生成开放重定向。 */
export function isInternalPath(value: string): boolean {
  return value.startsWith('/') && !value.startsWith('//') && !value.includes('\\');
}

/** 将 Schema 路径属性约束为站内路径。 */
export function pathProp(component: StoreComponentSchema, key: string, fallback: string): string {
  const value = textProp(component, key);
  return isInternalPath(value) ? value : fallback;
}

/** 对图片和跳转地址执行协议与控制字符白名单校验。 */
export function safeSchemaUrl(value: unknown): string {
  if (typeof value !== 'string' || !value) return '';
  const hasUnsafeCharacter = Array.from(value).some((character) => {
    const code = character.charCodeAt(0);
    return (
      code < 32 || character === '"' || character === "'" || character === '(' || character === ')'
    );
  });
  if (hasUnsafeCharacter) return '';
  if (isInternalPath(value)) return value;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'https:' || parsed.protocol === 'http:' ? parsed.toString() : '';
  } catch {
    return '';
  }
}

/** 读取经过安全校验的 Schema URL 属性。 */
export function urlProp(component: StoreComponentSchema, key: string): string {
  return safeSchemaUrl(textProp(component, key));
}
