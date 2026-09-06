/** 将整数分金额格式化为展示文本。 */
export function formatPrice(cents: number, currency = '¥'): string {
  if (!Number.isFinite(cents)) return '-';
  return `${currency}${(cents / 100).toFixed(2)}`;
}

/** 将展示用元转换为提交接口使用的整数分。 */
export function yuanToCents(yuan: number): number {
  return Math.round(yuan * 100);
}

/** 将整数分转换为数值元，用于非展示计算。 */
export function centsToYuan(cents: number): number {
  return cents / 100;
}
