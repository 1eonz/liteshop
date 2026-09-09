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
| plan-13 | integration and acceptance | E15 + E3.1.2 + E12 + E16.7 | 已完成本地门禁；覆盖率 59% 低于 CI 80%，真实供应商未接入 |

## 一期 1b 计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-14 | 支付、订单与商品状态安全整改 | 复审高风险、D1.1、D1.3.6、E3.1~E3.5、E16.3~E16.4 | 已完成，26 项后端测试通过 |
| plan-15 | 认证、验证码、Token 撤销与可信 IP | D2.1、E3.4、E16.6、E11.5 | 已完成，33 项后端测试通过 |
| plan-16 | 购物车一致性、清理与并发测试 | D1.3、E3.3、E16.3、E16.7 | 已完成，后端33测/H5全量验证通过 |
| plan-17 | 主题持久化、设置、搜索、库存分页与真实看板 | 4.2.1、4.2.10、D6.4、D6.5.3、E5.4 | 已完成，迁移/后端/Admin验证通过 |
| plan-18 | 售后退款完整闭环 | 4.2.7、D1.3.6、E3.8、E16.7 | 已完成本地闭环；真实供应商退款失败重试待补 |
| plan-19 | 会员列表、详情、标签与等级 | 4.2.8、D2.4、E7.1 | 已完成后端与 Admin 页面 |
| plan-20 | 通知中心与站内消息 | D6.1、E3.7、E15 | 已完成通知实体/API/H5 页面 |
| plan-21 | 商品评价与审核 | D6.2、D2.4、E7.1 | 已完成核心评价/审核/详情展示 |
| plan-22 | 商城低代码 Schema、渲染器与搭建器 | 4.3、D3.1、D3.2、E2.3、E8.2 | 已完成核心渲染和编辑链路；高级组件与生产数据源待补 |
| plan-23 | H5/Admin 一期缺失页面与服务化收藏 | 7.1、4.1、4.2、E15.1 | 已完成核心页面与收藏服务化 |
| plan-24 | PostgreSQL/Redis 集成、并发测试与商业验收 | E3.1.2、E12、E15、E16.7 | 本地基础设施、迁移和 3 项真实集成测试通过；全关键路径并发与覆盖率门禁待补 |
| plan-25 | 前端架构与组件体系收口 | E1.3、E2、E5.4、E15 | 已完成主要收口：features 领域 Hook、service 领域 API、路由懒加载与防抖兼容层已落地；本轮删除无调用方的 Admin 商品旧查询入口并补购物车恢复回归测试；完整 i18n/axe-core 深度覆盖仍待补 |
| plan-26 | 后端分层与关键路径测试收口 | E1.2、E3、E11.5、E15、E16 | 进行中：真实 PostgreSQL/Redis 集成 3 passed；API/Service 领域深拆、全关键路径并发和 80% 覆盖率仍待补 |

## 二期计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-27 | 官网 Next.js 低代码渲染、动态路由与 SEO | 4.4.1、4.4.4、4.4.5、4.4.6 | 已完成：官网页面、动态 Schema、SEO、sitemap、ISR 基础已落地 |
| plan-28 | 官网联系表单、导航与全局设置后端 | 4.4.2、4.4.3、D1.6、D2.4 | 已完成：联系表单、导航持久化、全局设置、幂等与 PostgreSQL 验证已落地 |
| plan-29 | 商城低代码扩展与后台页面管理 | 4.3、D3.3、D3.4、D6.7 | 已完成主要链路：页面 CRUD、草稿/发布、官网渠道、动态读取、ISR 通知、联系表单后台、官网画布/组件面板/动画配置；真实数据库种子发布 E2E 待补 |

## 后续缺口计划（状态以代码证据为准）

| Plan | 范围 | 优先级 | 当前状态 |
|---|---|---|---|
| plan-32 | 售后完整闭环：模型/迁移、7 状态机、H5 申请、Admin 审核、退货入库、幂等与集成测试 | P1 | 已完成本地闭环；单测 7 passed、真实售后幂等集成通过，供应商退款重试待补 |
| plan-33 | H5 SchemaRenderer 真实数据消费：首页接 Schema、商品/分类/轮播组件、加载/空/错误态 | P2 | 进行中：刷新/骨架、Schema 商品配置消费与发布响应 E2E 已完成；真实数据库发布 E2E、非首屏 lazy/Suspense 与请求瀑布仍待补 |
| plan-34 | 官网画布与动画配置：1200px 画布、官网组件面板、动画字段消费、发布预览 E2E | P2 | 进行中：主要链路和官网 ISR 鉴权 E2E 已完成；编辑器领域拆分、真实数据库种子发布/回滚 E2E 待补 |
| plan-35 | Admin UI 缺口：运费模板、评价审核、导航/全局设置、RBAC 管理 | P0/P3 | 已完成；Playwright 已覆盖 RBAC 403/409、运费多计费项、评价回复，完整 axe-core 待增强 |
| plan-36 | H5 体验缺口：改地址、支付倒计时、独立搜索、订单步骤条、通知/客服/设置、地址级联 | P0/P3 | 已完成核心体验和键盘/reduced-motion E2E；完整 i18n/axe-core 深度覆盖待增强 |
| plan-37 | ui-kit Phase 0/1：独立 token 桥接及最小组件集 | Phase 1 骨架已完成 | 进行中：独立包骨架完成；LiteShop token 桥接、调用方盘点/迁移和弹层 a11y 待补，重依赖与宪法调整需确认 |

## 三期计划

| Plan | 范围 | PRD 章节 | 当前状态 |
|---|---|---|---|
| plan-30 | 3D 组件基础、设备降级与性能约束 | 4.4.7、D8.3 | 已完成基础：动态导入、设备降级、静态回退和共享包测试通过；R3F/GLTF 仍待依赖确认 |
| plan-31 | 多租户、营销工具、物流轨迹与 AI 扩展 | 7.4、D4.5、D6.3.3 | 已完成可运行基础：优惠券、物流轨迹、AI 本地 Provider 与边界文档；第三方接入待决策 |

## 自动验收记录

- 后端：`ruff check`、`ruff format --check`、`python -m mypy .`、`pytest -q` 通过（70 passed，覆盖率 59%，低于 CI 80% 门禁）。
- Workspace：`pnpm -r typecheck`、`pnpm -r lint`、`pnpm -r test`、`pnpm -r build` 均通过；官网类型检查由 Turbo 先执行本包 build，保证 `.next/types` 可用。
- H5/Admin：各自 `tsc`、ESLint、Vitest、Vite build 均通过；H5 首屏 JS gzip 约 105KB，低于 200KB 门禁。
- E2E：Playwright 12/12 通过，覆盖 H5 首页/详情、交易主链路、Schema 预览、Admin 联系表单、RBAC 403/409、运费多计费项、评价回复、SKU 键盘焦点和官网 ISR 鉴权；真实数据库种子发布仍待补。
- OpenAPI：19 个 YAML 可由结构化解析器读取；实际 FastAPI 路由与契约逐项对照无遗漏，扩展契约已同步售后、RBAC、评价回复和页面渠道状态。
- 设计质量：`npx impeccable detect` 退出码 0；本轮新增交互使用 token、语义按钮、焦点恢复和 Escape 关闭。完整 axe-core 扫描仍待补。
- 架构复核：空 `features` 目录已补为商品/购物车/看板领域模块；Admin 登录 API 收敛至 service；API 层不再直接依赖设置仓储和领域异常。
- 安全：JWT 与支付回调签名不再使用代码内固定默认密钥；开发环境缺省生成进程随机值，staging/production 缺少环境密钥时拒绝启动。

> 2026-09-09 复核校正：命令级门禁和 12 项 E2E 已通过，但后端覆盖率仅 59%，真实支付/短信/物流供应商、官网真实数据库种子发布和完整 axe-core/i18n 仍未完成，当前不可宣称商业级生产就绪。

## 复核基线

- 复核方式：主 Agent 自动 5+1 复核；人工 review 按用户指令跳过。
- 验收耗时/返工次数/可留用比例：本轮未进行人工校准，因此不虚构三个数；命令级验收全部通过。

## 未决风险

- 本地 Docker、PostgreSQL 16、Redis 7 与 Alembic 往返迁移已验证；库存竞争、Redis NX 和售后幂等真实集成测试 3 passed，其余关键路径并发仍待补齐。
- 真实微信/支付宝 SDK、生产数据库仓储和真实支付沙箱尚未接入，当前回调为签名校验沙箱实现。
- 登录用户收藏已走服务端 API，游客收藏仍使用浏览器本地存储；需在产品规则中明确游客收藏的迁移或清理策略。
- settings/page schema 当前为进程内开发存储，落库属于后续迁移范围。
- 前端 plan-25 主要收口已完成；全面 i18n、axe-core 深度覆盖、官网真实数据库种子发布仍待补齐。
- H5/Admin 尚未安装 AGENTS.md 固定的 Ant Design、Tailwind、lucide、react-hook-form、zod 等依赖；这是既定技术栈与当前实现的偏差，安装和迁移需先取得用户确认。
- 后端 plan-26 已完成 Repository 第一批收口；`api/admin.py`、`services/admin.py`、`api/orders.py` 仍需按领域拆分，覆盖率 80% 门禁和更深关键路径并发 fixture 仍是上线前工作。
