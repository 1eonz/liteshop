import assert from 'node:assert/strict';
import test from 'node:test';
import {
  Button,
  EmptyState,
  Input,
  Skeleton,
  VERSION,
} from '../dist/index.js';
import { Button as PcButton } from '../dist/pc/index.js';
import { Button as MobileButton } from '../dist/mobile/index.js';

test('导出基础组件和版本号', () => {
  assert.equal(VERSION, '0.1.0');
  assert.equal(typeof Button, 'function');
  assert.equal(typeof Input, 'function');
  assert.equal(typeof EmptyState, 'function');
  assert.equal(typeof Skeleton, 'function');
  assert.equal(PcButton, Button);
  assert.equal(MobileButton, Button);
});

test('组件可以创建 React 元素且保留语义标签类型', async () => {
  const { createElement } = await import('react');
  const button = createElement(Button, { children: '保存', type: 'submit' });
  const input = createElement(Input, { label: '名称', name: 'name' });
  const empty = createElement(EmptyState, { title: '暂无数据' });
  const skeleton = createElement(Skeleton, { label: '正在加载' });

  assert.equal(button.type, Button);
  assert.equal(input.type, Input);
  assert.equal(empty.type, EmptyState);
  assert.equal(skeleton.type, Skeleton);
});
