/** 将整数分格式化为后台展示金额。 */
export function formatPrice(priceCents: number): string {
  return `¥${(priceCents / 100).toFixed(2)}`;
}
