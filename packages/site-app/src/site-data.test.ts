import { describe, expect, it } from 'vitest';
import { siteTitle } from './site-data';

describe('官网基础信息', () => {
  it('提供品牌名称', () => {
    expect(siteTitle).toBe('LiteShop');
  });
});
