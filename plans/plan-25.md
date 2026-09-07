# Plan 25：前端架构与组件体系收口

> PRD 章节：E1.3+E2+E5.4+E15

## 背景

一期功能代码已经能够通过格式化、Lint、类型检查、构建和基础冒烟测试，但本轮复核确认前端仍存在职责集中、重复实现、测试覆盖不足和既定技术栈未落地的问题。该计划完成前，不得把前端标记为商业级验收通过。

## 任务清单

- [x] 删除初始骨架遗留的空 `src/app`、`src/shared/*` 目录，统一使用 `pages/components/features/hooks/service/store/utils/router`。
- [x] 将 Admin 的 `useAdminQueries.ts` 按商品、订单、库存、会员、设置等领域拆到对应 `features/*/api`，旧文件仅保留兼容导出。
- [x] 将 Admin 的 `service/admin.ts` 按领域拆分为独立 API 模块，并保留兼容聚合出口。
- [ ] 拆分 Admin 订单、设置、库存页面和 H5 购物车、订单确认、地址页面中的独立视图与表单组件；页面只负责路由参数、状态编排和布局组合。
- [ ] 收敛重复的 `ProductCard` 与 `formatPrice`，共享类型、金额格式化和跨页面组件只保留一个事实源。
- [x] 将 H5/Admin 路由改为页面级懒加载，并为路由加载提供稳定的 Skeleton/Suspense 状态。
- [x] 为 `useDebounceAction` 补充 `"use client"`、并发点击、异常释放、卸载和冷却期测试；应用包只保留兼容导出。
- [ ] 对所有 HTTP 写操作做静态覆盖检查：统一请求 ID、mutation `retry: 0`、按钮执行及冷却期间 disabled。
- [ ] 建立 i18n 资源层，移除页面和共享组件中的硬编码展示中文。
- [ ] 按 AGENTS.md 固定技术栈补齐 H5/Admin UI、图标、表单和 Tailwind 依赖；安装前取得用户依赖变更确认。
- [ ] 将业务 CSS 中可复用的尺寸、边框、断点和层级值收敛为 Design Token，禁止自由硬编码视觉值和 z-index。
- [ ] 增加 H5/Admin 组件、Hook、路由守卫、错误态、写操作防抖测试，以及 Admin E2E、键盘导航和 axe-core a11y 测试。
- [x] 修复 E2E 配置中的绝对工作区路径，保证换电脑和 CI 可运行。

## 验收标准

- [ ] `features` 中每个领域模块均有真实模型、查询或业务能力，不保留名存实亡目录。
- [ ] 页面文件原则上只做编排；超过 180 行时必须说明不可再拆的理由或继续拆分。
- [ ] 无重复组件、金额格式化函数、领域类型、枚举和 API 封装。
- [ ] 所有写操作满足防抖、禁重入、请求幂等键和 `retry: 0`。
- [ ] H5/Admin 路由产生独立页面 chunk，首屏 gzip 继续低于 200KB。
- [ ] 前端显示文本走 i18n 资源，业务 CSS 视觉值全部来自 Token。
- [ ] H5/Admin 单元与交互测试覆盖核心交易和后台操作；E2E 覆盖 H5、Admin、键盘和 a11y。
- [x] `pnpm lint && pnpm typecheck && pnpm test && pnpm build` 全部通过；改动文件已由 `npx prettier@3.6.2` 校验。
