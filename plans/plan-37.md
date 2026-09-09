# Plan 37：ui-kit Phase 0/1

> PRD 章节：E2+E4.3+E8.2
> 当前状态：**Phase 1 骨架已完成，迁移与重依赖待确认**
> 强制关卡：修改 AGENTS.md、把现有应用迁移到 ui-kit、引入 Radix/Framer Motion/RHF/zod 前必须获得用户确认。

## 目标

在不复制业务组件和 token 的前提下，建立可跨项目复用的最小 UI 基础层。

## 任务清单

- [ ] 先决策 AGENTS.md 中 antd/antd-mobile 与 ui-kit 的最终技术栈条款；本阶段未修改宪法，保留人工确认关卡。
- [ ] 盘点 shared-components 调用方，定义 ui-kit 与业务组件边界及迁移顺序。
- [x] 修复 shared-tokens 的重复字号和 z-index token；gallery 作用域因三端同步迁移风险暂保留，shared-tokens 仍是 LiteShop 业务 token 唯一事实源。
- [ ] 评估候选依赖的包体积、许可证、SSR/React 18 兼容、维护活跃度和 a11y 能力。
- [x] Phase 1 实现 Button、Input、Skeleton、EmptyState；Toast 达到第二个稳定调用方后再加入。
- [x] 创建 `pc`/`mobile` 薄出口，暂不实现没有真实调用方的平台专属组件。
- [x] 每个已实现组件提供 Props interface、中文 TSDoc、单测冒烟覆盖和 CHANGELOG。
- [ ] Storybook/stories：当前没有文档站调用方，待真实文档站需求出现后补齐。
- [x] ui-kit 不依赖 `@liteshop/*`；LiteShop 后续通过桥接变量消费 shared-tokens，独立复用时使用 fallback。
- [ ] 弹层类组件验证焦点移入/恢复、Escape、背景隔离、滚动锁、reduced motion 和触摸目标。
- [ ] 逐组件迁移调用方，禁止一次性全量替换和同时维护两套同名组件。

## 验收标准

- [x] Phase 1 未引入重依赖，React 仅作为 peer dependency；后续架构和依赖变更仍需确认。
- [x] 基础组件为迁移候选，不包含业务逻辑；平台专属组件遵守真实调用方和 Rule of Three。
- [ ] LiteShop 内通过宿主映射接入 shared-tokens（当前尚未接入）；独立包保留 `--ui-*` fallback，不把 fallback 当作业务 token 源。
- [x] 构建产物支持 ESM、类型声明和按子路径 tree-shaking。

## 验证命令

```powershell
pnpm --filter @liteshop/ui-kit build
pnpm --filter @liteshop/ui-kit test
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```

## 本次交付记录

- 新增 `packages/ui-kit`，版本 `0.1.0`。
- 已验证：`pnpm --dir packages/ui-kit build`、`typecheck`、`lint`、`test` 全部通过（2 tests passed）。
- 根级 `pnpm typecheck`、`pnpm lint`、`pnpm test`、`pnpm build` 全部通过，Turbo 已将 ui-kit 纳入 8 个 workspace 包。
- 未修改现有 H5/Admin/Site/shared-components，未引入 Radix、Framer Motion、react-hook-form、zod 或其他重依赖。
