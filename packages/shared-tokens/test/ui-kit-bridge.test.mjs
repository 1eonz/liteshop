import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

test('UI Kit 桥接只引用 LiteShop 设计变量', async () => {
  const css = await readFile(new URL('../src/ui-kit-bridge.css', import.meta.url), 'utf8');
  assert.match(css, /--ui-color-primary:\s*var\(--color-primary-500\)/);
  assert.match(css, /--ui-spacing-4:\s*var\(--spacing-4\)/);
  assert.doesNotMatch(css, /#[\da-f]{3,8}\b/i);
  assert.doesNotMatch(css, /\b\d+(?:\.\d+)?px\b/);
});
