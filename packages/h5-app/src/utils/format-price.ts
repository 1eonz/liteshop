/** 将整数分格式化为展示文本，禁止在页面内重复金额计算。 */
export function formatPrice(priceCents: number): string {
  return `¥${(priceCents / 100).toFixed(2)}`;
}
