# Plan 37：ui-kit Phase 0/1

> PRD 章节：E2+E4.3+E8.2
> 当前状态：架构待确认
> 强制关卡：修改 AGENTS.md、创建 `packages/ui-kit`、引入 Radix/Framer Motion/RHF/zod 前必须获得用户确认。

## 目标

在不复制业务组件和 token 的前提下，建立可跨项目复用的最小 UI 基础层。

## 任务清单

- [ ] 先决策 AGENTS.md 中 antd/antd-mobile 与 ui-kit 的最终技术栈条款，不在冲突状态下实施。
- [ ] 盘点 shared-components 调用方，定义 ui-kit 与业务组件边界及迁移顺序。
- [ ] 修复 shared-tokens 的重复字号、gallery 作用域和 z-index token；保持其为唯一业务 token 源。
- [ ] 评估候选依赖的包体积、许可证、SSR/React 18 兼容、维护活跃度和 a11y 能力。
- [ ] Phase 1 只实现有真实调用方的 Button、Input、Skeleton、EmptyState；Toast 达到第二个稳定调用方后再加入。
- [ ] 不预建空的 pc/mobile 目录；出现 Select/Dialog 或 ActionSheet/BottomSheet 的真实调用方后再创建对应子路径。
- [ ] 每个组件提供 Props interface、TSDoc、受控/非受控协议（如适用）、单测、stories 和 CHANGELOG。
- [ ] ui-kit 不依赖 `@liteshop/*`；LiteShop 通过桥接变量消费 shared-tokens，独立复用时才使用 fallback。
- [ ] 弹层类组件验证焦点移入/恢复、Escape、背景隔离、滚动锁、reduced motion 和触摸目标。
- [ ] 逐组件迁移调用方，禁止一次性全量替换和同时维护两套同名组件。

## 验收标准

- [ ] 未确认架构和依赖前，本计划不产生 workspace 代码或依赖变更。
- [ ] 每个进入 ui-kit 的组件至少有真实调用方和复用理由，不创建展示性空壳。
- [ ] 主题值只有一个事实源，LiteShop 内不存在第二套颜色/字号/间距默认值。
- [ ] 构建产物支持 ESM、类型声明和按子路径 tree-shaking。

## 验证命令

```powershell
pnpm --filter @liteshop/ui-kit build
pnpm --filter @liteshop/ui-kit test
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```
