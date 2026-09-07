# LiteShop Project Context

> 由 project-radar 增量更新：2026-09-07。本文件是主 Agent 的最小上下文入口，子 Agent 若重新启用必须先读取相关章节。

## 代码索引

项目结构模式：pnpm/Turborepo monorepo + FastAPI backend。

- `packages/shared-types/`：导出订单、支付、库存、商品、分类、RBAC、审计和整数分工具；前端禁止重复声明领域类型。
- `packages/shared-tokens/`：提供颜色、图表、字体、间距、圆角、阴影和画廊风格 CSS 变量。
- `packages/shared-components/`：提供 Button、EmptyState、ProductCard 等基础组件。
- `packages/h5-app/`：按 `pages/components/features/hooks/service/store/utils/router` 分层；`features/catalog` 承载商品查询、首页配置，`features/cart` 承载购物车领域模型；商品详情的轮播、评价、SKU 抽屉位于 `pages/product-detail/components`，购物车商品行位于 `pages/cart/components`；认证状态统一由 `store/session.ts` 管理，地址、通知、订单详情和支付页面有登录守卫，访客购物车和商品浏览保持匿名可用。
- `packages/admin-app/`：按同样分层，并在 `features/dashboard`、`features/contact` 承载看板和官网联系表单模型；看板、商品列表/真实新建/编辑、分类、订单、库存、审计、RBAC、设置、页面搭建、联系表单已接入；认证状态由 `store/session.ts` 管理，`AdminLayout` 对后台路由执行管理员令牌守卫，写操作统一走共享 `useDebounceAction`。
- `packages/shared-components/`：提供 `Button`、`EmptyState`、`FeedbackState`、`ErrorState`、`ProductCard` 和唯一的 `useDebounceAction` 实现。
- `packages/site-app/`：Next.js App Router 官网，页面 Schema 位于 `src/site-data.ts`，组件渲染器位于 `src/components/SiteRenderer.tsx`，包含动态 slug、SEO、sitemap、robots 和联系表单 Route Handler。
- `packages/shared-3d-components/`：三期 3D 场景配置、设备降级和速度约束工具；官网通过动态组件接入轻量回退，当前不依赖 Three.js/R3F。
- `backend/app/`：FastAPI 分层骨架：api/core/models/schemas/services/repositories/tasks/enums/errors；订单、库存、支付、用户、设置和后台 API 已实现，领域异常集中于 `errors/domain.py`，主题设置由 `services/settings.py` 编排。
- `backend/alembic/`：异步 Alembic 迁移及可逆迁移文件；当前 head 为 `20260907_094000`，页面渠道路由使用复合唯一约束并增加草稿/发布状态。
- `backend/integration_tests/`：显式启用的真实 PostgreSQL/Redis 验收，`scripts/test.ps1 -Integration` 运行库存竞争和 Redis NX 幂等测试；默认单元测试不会自动依赖基础设施。
- `tests/e2e/`：Playwright H5 冒烟测试。
- `docs/api-contracts/v1/`：18 个 OpenAPI 文件，包含官网页面、联系表单、导航、营销、物流、评价和后台接口契约。
- `plans/`：plan-01 到 plan-13 及索引，覆盖 1a 需求。
- `docs/架构说明.md`：CRM 风格目录对齐方案、前端数据流和后端分层边界。

## PRD 分层读指引

- 第 1 层：主 Agent 读 PRD 目录、§7.1 MVP 清单、§D8.1 阶段表。
- 第 2 层：主 Agent 按 plan 读取对应附录章节，并把需求翻译到 plan 文件。
- 第 3 层：子 Agent 只读 `plans/plan-{i}.md`，不一次读取完整 PRD。
- 当前总体 PRD：`docs/PRD-v1.3.md`；工作流机制唯一权威：`AGENTS.md §八`。

## 风险清单

### 已处理

- ✅ 实际 FastAPI 1a 路由与 OpenAPI 契约逐项对照，无 1a 漏项；1b 预留接口仍保留文档但不计入本期覆盖。
- ✅ workspace `typecheck` 已依赖本包 `build`，官网 `.next/types` 缺失不会再导致干净环境误报。
- ✅ H5 购物车、确认订单和商品详情的权限/业务错误不再静默回退演示数据；错误态提供重试或返回路径。
- ✅ JWT 与支付回调签名不再使用固定代码默认密钥；生产/预发布缺失环境密钥会拒绝启动。

- ✅ 生产/预发布环境若未启用 `LITESHOP_USE_DATABASE` 会拒绝启动；前端演示回退仅在 Vite 开发模式启用。
- ✅ API 不再直接依赖仓储异常或系统设置仓储；前端登录不再绕过 service 层。
- ✅ 前端认证令牌统一由各端 `store/session.ts` 管理；后台不再复用 H5 用户令牌，后台布局和受保护页面均有认证守卫。
- ✅ H5 登录验证码按钮实现 60 秒前端冷却，发送动作仍由 `useDebounceAction` 防重复点击，后端继续执行 Redis/接口限流。
- ✅ 官网基础动态路由、SEO 元数据、sitemap/robots 与联系表单幂等入口已建立。
- ✅ 官网导航、全局设置、页面管理 CRUD、A/B 变体和转化事件已建立。
- ✅ 3D 组件动态导入和设备降级已接入官网；优惠券、物流轨迹、AI 本地 Provider 已建立可插拔基础。

### 当前未处理

- ✅ Docker Desktop Engine 已恢复；PostgreSQL 16 与 Redis 7 已通过本机 Compose healthcheck，Alembic 已完成 upgrade/downgrade 往返；真实库存竞争与 Redis NX 幂等集成测试 `2 passed`。
- 真实生产数据库仓储、微信/支付宝 SDK 和支付沙箱尚未接入；当前支付回调为本地签名验证实现。
- 收藏为浏览器本地存储；settings/page schema 为开发进程内存储；均属于后续持久化范围。
- 官网动态页面 API、ISR revalidate、联系表单后台处理和 `DRAFT/PUBLISHED` 发布状态已接入；真实数据库种子发布 E2E、通知渠道仍待补齐。
- Three.js/R3F、GSAP、Lenis、Framer Motion 属于待确认的新依赖；当前使用 CSS 与原生 API 保持可构建。
- 多租户遵循独立部署优先；共享数据库 `tenant_id` 隔离、真实物流/AI/营销供应商仍待决策。
- Impeccable 完整 HTML/CSS 解析模块在当前环境缺失，但机械 detector 已对 H5/Admin 返回空结果。
- 页面层仍保留少量直接调用 `service` 方法的交易编排代码（未出现组件内裸 Axios）；H5 购物车、地址、结算和 Admin 主要领域已有 `features/*/api` 出口，后续若交易规则继续增长继续下沉。
- 页面首页标记已按 `store/site` 渠道隔离清理，避免切换一端首页误取消另一端首页。
- Admin `useAdminQueries.ts` 与 `service/admin.ts` 已收敛为兼容出口，真实实现位于各 `features/*/api` 与 `service/admin/<domain>.ts`；后端 `api/admin.py`/`api/orders.py` 仍为历史聚合文件，属于 plan-26 后续拆分项；拆分需保持契约快照和路由标签不变。
- H5/Admin 中的兼容入口 `src/useDebounceAction.ts` 和 `hooks/useDebounceAction.ts` 仍保留用于旧调用方，不得再增加新的实现或入口。

## Agent 工作流适配建议

- 当前任务已按主 Agent 直接串行执行；若重新启用子 Agent，仍应按 AGENTS.md §8.3 的领地规则逐 plan 启动，不并行修改同一领域。
- 每个子 Agent 启动前注入本文代码索引与对应契约摘要；完成后执行 liteshop-verify 的 5+1 检查。
- backend 重点执行 ruff、mypy、pytest；前端重点执行 tsc、lint、test、build；集成执行 Playwright。
- 每 3 个 plan 完成后重新扫描；一期 plan-01~26 已完成主要收口，二期/三期跟踪 plan-27~31。

## 完整 MVP 清单（验收对照用）

来源：PRD §7.1，仅登记 `[1a]` 范围，`[1b]` 不计入本期遗漏。

- 商城：商品分类/列表/详情、SKU 选择、购物车、订单确认/提交、支付创建、订单列表/详情、取消订单、确认收货、搜索。
- 后台：数据看板、分类管理、SPU/SKU 管理、订单管理、库存管理、系统设置基础项。
- 工程：订单状态机、库存原子扣减/回滚、支付回调验签/幂等/金额校验、购物车 Redis、订单超时取消、操作日志。

## 需求覆盖矩阵

| PRD 需求点 | PRD 章节 | 对应任务 | 是否覆盖 |
|---|---|---|---|
| shared-types、tokens、components | D2.4、E2、E8.2 | plan-01~03 | 已覆盖 |
| backend 认证/基础骨架/操作日志 | D2.1~D2.5、E3.4、E3.7 | plan-04 | 已覆盖 |
| 商品与三层库存 | D1.1.1、D1.5、E3.1、E3.2 | plan-05 | 已覆盖 |
| 订单、支付、后端幂等 | D1.1、D1.3.6、E3.3、E3.5、E3.8、E16.3 | plan-06 | 已覆盖 |
| H5 商城浏览与交易 | D4.1、D4.4、D6.3、E16.2 | plan-07~09 | 已覆盖 |
| 后台 RBAC、商品、订单、库存、看板 | D1.4、D2.4、D6.4、D6.5.3、E7.1 | plan-10~12 | 已覆盖 |
| 集成测试与 1a 验收 | E15、E3.1.2、E12、E16.7 | plan-13 | 已覆盖 |
