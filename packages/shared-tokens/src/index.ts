/** LiteShop 共享设计令牌，主题通过 CSS 变量覆盖。 */
export const designTokens = {
  colorPrimary: 'var(--color-primary)',
  colorInk: 'var(--color-ink)',
  colorMuted: 'var(--color-muted)',
  spacingUnit: 'var(--spacing-1)',
  radiusCard: 'var(--radius-card)',
} as const;

export const chartColors = [
  'var(--chart-color-1)',
  'var(--chart-color-2)',
  'var(--chart-color-3)',
  'var(--chart-color-4)',
  'var(--chart-color-5)',
] as const;
