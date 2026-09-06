# LiteShop 一期计划索引（1a + 1b）

按 AGENTS.md §8.3 的计划范围完成 1a 期 13 个计划。本轮由主 Agent 直接串行复核，未启动子 Agent，也未执行人工逐行 review。

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-01 | shared types/enums | D2.4 + E2 + E8.2 | 已完成，构建/类型测试通过 |
| plan-02 | design tokens | D2.4 + E2 + E8.2 | 已完成，变量与构建检查通过 |
| plan-03 | shared components | D2.4 + E2 + E8.2 | 已完成，构建/测试通过 |
| plan-04 | backend skeleton/auth/logging | D2.1~D2.5 + E3.4 + E3.7 + E7.2 + E16.6 | 已完成，ruff/mypy/pytest 通过 |
| plan-05 | products and three-layer inventory | D1.1.1 + D1.5 + E3.1 + E3.2 | 已完成，库存原子更新、流水与后台台账已接入 |
| plan-06 | orders and payments | D1.1 + D1.3.6 + E3.3 + E3.5 + E3.8 + E16.3 + E16.4.1~4.2 | 已完成，状态机、金额校验、回调验签和幂等已覆盖 |
| plan-07 | H5 shell/loading states | D4.1 + D4.4 + E1.3 + E15.1#18 | 已完成，路由与页面状态骨架通过构建 |
| plan-08 | H5 product browsing/search | 4.1.2 + D6.3 + E15.1#18 | 已完成，分类、搜索、详情、SKU 抽屉和收藏入口已接入 |
| plan-09 | cart/checkout/payment | D1.3 + D6.5.1~2 + D6.6 + E16.2 + E16.4.3 | 已完成，购物车、确认订单、支付创建和错误态已接入 |
| plan-10 | admin shell/RBAC/logs | D1.4 + D2.4 + E7.1 + E15.1#16-17 | 已完成，权限、角色和审计查询已接入 |
| plan-11 | admin products/orders | 4.2.2~3 + D2.4 + E7.1 + E3.8 + E16.5 | 已完成，分类、SPU/SKU、新建、编辑、发货、取消、备注和改价已接入 |
| plan-12 | admin inventory/freight/dashboard/settings | 4.2.1/4/10 + D6.4 + D6.5.3 + E5.4 + E15.1#12-15 | 已完成，看板、库存流水、系统设置和功能开关已接入 |
| plan-13 | integration and acceptance | E15 + E3.1.2 + E12 + E16.7 | 已完成，后端、workspace、E2E、契约和 Impeccable 检查通过 |

## 一期 1b 计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-14 | 支付、订单与商品状态安全整改 | 复审高风险、D1.1、D1.3.6、E3.1~E3.5、E16.3~E16.4 | 已完成，26 项后端测试通过 |
| plan-15 | 认证、验证码、Token 撤销与可信 IP | D2.1、E3.4、E16.6、E11.5 | 已完成，33 项后端测试通过 |
| plan-16 | 购物车一致性、清理与并发测试 | D1.3、E3.3、E16.3、E16.7 | 已完成，后端33测/H5全量验证通过 |
| plan-17 | 主题持久化、设置、搜索、库存分页与真实看板 | 4.2.1、4.2.10、D6.4、D6.5.3、E5.4 | 已完成，迁移/后端/Admin验证通过 |
| plan-18 | 售后退款完整闭环 | 4.2.7、D1.3.6、E3.8、E16.7 | 已完成核心退款 worker/状态/库存回补 |
| plan-19 | 会员列表、详情、标签与等级 | 4.2.8、D2.4、E7.1 | 已完成后端与 Admin 页面 |
| plan-20 | 通知中心与站内消息 | D6.1、E3.7、E15 | 已完成通知实体/API/H5 页面 |
| plan-21 | 商品评价与审核 | D6.2、D2.4、E7.1 | 已完成核心评价/审核/详情展示 |
| plan-22 | 商城低代码 Schema、渲染器与搭建器 | 4.3、D3.1、D3.2、E2.3、E8.2 | 已完成基础 Schema/渲染/编辑器，增强项待补 |
| plan-23 | H5/Admin 一期缺失页面与服务化收藏 | 7.1、4.1、4.2、E15.1 | 已完成核心页面与收藏服务化 |
| plan-24 | PostgreSQL/Redis 集成、并发测试与商业验收 | E3.1.2、E12、E15、E16.7 | 基础设施与迁移往返已完成，真实并发覆盖待补 |
| plan-25 | 前端架构与组件体系收口 | E1.3、E2、E5.4、E15 | 主要架构项已完成，i18n/a11y 深度覆盖待补 |
| plan-26 | 后端分层与关键路径测试收口 | E1.2、E3、E11.5、E15、E16 | Repository 第一批已完成，大文件拆分与真实并发待补 |

## 二期计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-27 | 官网 Next.js 低代码渲染、动态路由与 SEO | 4.4.1、4.4.4、4.4.5、4.4.6 | 进行中：官网页面与 18 类组件基础渲染已落地 |
| plan-28 | 官网联系表单、导航与全局设置后端 | 4.4.2、4.4.3、D1.6、D2.4 | 进行中：联系表单 API、幂等与 PostgreSQL 表已落地 |
| plan-29 | 商城低代码扩展与后台页面管理 | 4.3、D3.3、D3.4、D6.7 | 待实施：需补编辑器持久化、模板和变体 |

## 三期计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-30 | 3D 组件基础、设备降级与性能约束 | 4.4.7、D8.3 | 进行中：共享 3D 配置工具已落地，R3F 依赖待确认 |
| plan-31 | 多租户、营销工具、物流轨迹与 AI 扩展 | 7.4、D4.5、D6.3.3 | 待实施：依赖业务与基础设施决策 |

## 自动验收记录

- 后端：`ruff check`、`ruff format --check`、`mypy app`、`pytest -q` 均通过，33 passed（含 plan-14/15 安全测试）。
- Workspace：`pnpm -r typecheck`、`pnpm -r lint`、`pnpm -r test`、`pnpm -r build` 均通过；官网类型检查由 Turbo 先执行本包 build，保证 `.next/types` 可用。
- H5/Admin：各自 `tsc`、ESLint、Vitest、Vite build 均通过；H5 首屏 JS gzip 约 105KB，低于 200KB 门禁。
- E2E：Playwright 冒烟 2/2 通过。
- OpenAPI：14 个 YAML 可由结构化解析器读取；实际 FastAPI 1a 路由与契约逐项对照无遗漏。after-sale/review/notification 契约属于 1b 预留接口。
- 设计质量：Impeccable detector 对 H5/Admin 返回 `[]`；本轮新增交互使用 token、语义按钮、焦点恢复和 Escape 关闭。
- 架构复核：空 `features` 目录已补为商品/购物车/看板领域模块；Admin 登录 API 收敛至 service；API 层不再直接依赖设置仓储和领域异常。
- 安全：JWT 与支付回调签名不再使用代码内固定默认密钥；开发环境缺省生成进程随机值，staging/production 缺少环境密钥时拒绝启动。

> 2026-09-06 复核校正：以上命令通过只能证明当前代码可格式化、可编译和可运行基础冒烟，不能证明前端架构或交互覆盖完整。H5/Admin 目前各只有 2 条单测，E2E 只有 2 条 H5 冒烟；前端架构缺口统一进入 plan-25。

## 复核基线

- 复核方式：主 Agent 自动 5+1 复核；人工 review 按用户指令跳过。
- 验收耗时/返工次数/可留用比例：本轮未进行人工校准，因此不虚构三个数；命令级验收全部通过。

## 未决风险

- 本地 Docker、PostgreSQL 16、Redis 7 与 Alembic 往返迁移已验证；真实数据库并发测试仍待补齐。
- 真实微信/支付宝 SDK、生产数据库仓储和真实支付沙箱尚未接入，当前回调为签名校验沙箱实现。
- 登录用户收藏已走服务端 API，游客收藏仍使用浏览器本地存储；需在产品规则中明确游客收藏的迁移或清理策略。
- settings/page schema 当前为进程内开发存储，落库属于后续迁移范围。
- 前端 plan-25 主要收口已完成；全面 i18n、Admin E2E/axe-core、官网动态数据接入仍待补齐。
- H5/Admin 尚未安装 AGENTS.md 固定的 Ant Design、Tailwind、lucide、react-hook-form、zod 等依赖；这是既定技术栈与当前实现的偏差，安装和迁移需先取得用户确认。
- 后端 plan-26 已完成 Repository 第一批收口；`api/admin.py`、`services/admin.py`、`api/orders.py` 仍需按领域拆分，当前 35 条测试总覆盖率约 60%。
