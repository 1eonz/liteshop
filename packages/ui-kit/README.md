# @liteshop/ui-kit

可独立迁移的基础 UI 组件包。当前是 Phase 1 最小骨架，包含 `Button`、`Input`、`EmptyState` 和 `Skeleton`。

## 使用

```tsx
import { Button, Input, Skeleton } from '@liteshop/ui-kit';
import '@liteshop/ui-kit/tokens.css';

export function Example() {
  return (
    <form>
      <Input label="名称" name="name" />
      <Button type="submit">保存</Button>
      <Skeleton label="正在加载" />
    </form>
  );
}
```

组件只依赖 React peer dependency，不依赖 LiteShop 业务包、Radix、Framer Motion、RHF 或 Zod。宿主项目可以把自己的设计系统变量映射到 `--ui-*`；在独立项目中也可以直接使用 `src/tokens.css` 提供的 fallback。

## 本地验证

```bash
pnpm build
pnpm typecheck
pnpm lint
pnpm test
```
