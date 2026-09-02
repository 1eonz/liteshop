# LiteShop Agent 协作规则（项目宪法）

> 本文件是所有 Agent（主 Agent 与子 Agent）的强制约束。Agent 启动时必须先读本文件，再读 plans/plan-{i}.md。
> 详细设计依据见 `docs/PRD-v1.3.md`（附录 D 数据模型/契约、附录 E 工程约束）。

---

## 一、技术栈（不可更改）

### 1.1 前端

| 分类 | 选型 | 版本 |
|---|---|---|
| 框架 | React 18 | 18.x（函数组件 + Hooks，禁 class） |
| 官网框架 | Next.js 14+ App Router | 14.x |
| 构建 | Vite 5+ | 5.x |
| 语言 | TypeScript 5+ | 5.x |
| 包管理 | pnpm + workspace | 9.x |
| H5 UI 库 | Ant Design Mobile 5 | 5.x |
| 后台 UI 库 | Ant Design 5 | 5.x |
| 官网 UI | Tailwind CSS v4 + shadcn/ui | v4 |
| 样式方案 | Tailwind CSS v4 | v4 |
| 动态样式 | CSS 变量 + 内联 style（禁 Tailwind 动态拼接类） | — |
| 状态管理 | Zustand | 5.x |
| 服务端状态 | React Query (TanStack Query) | 5.x |
| 拖拽 | dnd-kit | 6.x |
| 不可变更新 | Immer | 5.x |
| UI 动画 | Framer Motion | 11.x |
| 平滑滚动 | Lenis | 1.x（官网） |
| 滚动动画 | GSAP + ScrollTrigger | 3.x（官网） |
| 图标 | lucide-react | latest |
| 路由 | React Router 6 | 6.x |
| HTTP | Axios | 1.x |
| 表单 | react-hook-form + zod | latest |
| 代码规范 | ESLint + Prettier + Husky + lint-staged | latest |

### 1.2 后端

| 分类 | 选型 | 版本 |
|---|---|---|
| 语言 | Python | 3.12 |
| Web 框架 | FastAPI | 0.115+ |
| ORM | SQLAlchemy 2.0（async） | 2.0+ |
| 迁移 | Alembic | 1.13+ |
| 数据库 | PostgreSQL | 16 |
| 缓存/锁 | Redis | 7 |
| 任务队列 | Celery + Redis | 5.x |
| 认证 | python-jose（JWT）+ passlib（bcrypt） | latest |
| 支付 | wechatpay-python + alipay-sdk | latest |
| 文件存储 | 阿里云 OSS / 腾讯云 COS | latest |
| 短信 | 阿里云短信 / 腾讯云短信 | latest |
| 邮件 | SMTP | — |
| 数据校验 | Pydantic v2 | 2.x |
| 日志 | structlog | 24.x |
| 部署 | Docker + Docker Compose | latest |
| Web 服务器 | Nginx | 1.24+ |
| ASGI | Uvicorn / Gunicorn | latest |

### 1.3 基础设施

- 云服务器：阿里云/腾讯云 4C8G 起步
- 官网部署：Vercel 或自托管 + CDN
- 对象存储：阿里云 OSS / 腾讯云 COS + CDN
- 监控：Sentry + Prometheus + Grafana

---

## 二、领地规则（硬性）

每个 Agent 只能修改自己领地内的文件，跨领地需求写进 final summary 的阻塞项，**不得自行跨领地修改**。

| 角色 | 只能修改的目录 |
|---|---|
| backend-agent | `backend/` |
| h5-agent | `packages/h5-app/` |
| site-agent | `packages/site-app/` |
| admin-agent | `packages/admin-app/` |
| shared-agent | `packages/shared-types/`、`shared-tokens/`、`shared-components/` |
| 3d-agent | `packages/shared-3d-components/`（三期，独立包） |
| verification-agent | `tests/e2e/`（只新建，禁改业务代码） |
| main-agent（主 Agent） | `plans/`、`docs/`、`AGENTS.md`（不写业务代码） |

**类型一律从 `@liteshop/shared-types` 导入，禁止重复定义。**
**API 一律遵循 `docs/api-contracts/v1/` 下的 OpenAPI 定义。**

---

## 三、目录结构

主 Agent 现场生成项目骨架时按以下结构创建，开发者不需要预先创建：

```
liteshop/
├── AGENTS.md                     # 本文件（Agent 宪法）
├── 提示词.md                     # IDE 启动主 Agent 的入口提示词
├── docs/
│   ├── PRD-v1.3.md               # 产品需求文档（v1.3 含附录 D/E）
│   ├── 环境准备清单.md           # 电脑环境/软件/依赖清单
│   ├── 工作流文档-v2.0.md        # IDE 多 Agent 调度机制
│   ├── 设计规范.md               # Design System 完整规范（色彩/字体/间距/圆角/阴影/组件）
│   ├── Skills安装指南.md         # 12 个核心 skills 清单 + 市面分析 + 使用时机
│   ├── api-contracts/v1/         # OpenAPI 契约（阶段 0 产出）
│   ├── error-codes.md            # 错误码表（PRD D2.2）
│   └── verify-commands.md        # 各端验证命令
├── plans/                        # 计划拆解（主 Agent 现场写）
├── packages/
│   ├── shared-types/             # 【shared 领地】
│   ├── shared-tokens/            # 【shared 领地】
│   ├── shared-components/        # 【shared 领地】
│   ├── shared-3d-components/     # 【3d 领地，三期】
│   ├── h5-app/                   # 【h5 领地】
│   ├── site-app/                 # 【site 领地，二期】
│   └── admin-app/                # 【admin 领地】
├── backend/                      # 【backend 领地】
│   └── app/{api,core,models,schemas,services,repositories,tasks,enums,errors,main}.py
├── tests/e2e/                    # 【verification 领地】
├── scripts/                      # 自动化脚本（主 Agent 生成）
├── docker-compose.yml
├── pnpm-workspace.yaml
├── turbo.json
└── package.json
```

**当前已存在的文档文件**（你换电脑后只需带这几个文件，其他由主 Agent 生成）：

- `AGENTS.md`（本文件）
- `操作手册.md`（你本人看的逐步 IDE 操作指南，8 步从环境到上线）
- `提示词.md`（主 Agent 入口提示词，复制粘贴到对话窗即可启动）
- `docs/PRD-v1.3.md`（产品需求 + 详细设计附录 D/E）
- `docs/工作流文档-v2.0.md`（IDE 多 Agent 调度机制）
- `docs/环境准备清单.md`（电脑环境/软件/依赖）
- `docs/设计规范.md`（Design System 完整规范：色彩/字体/间距/圆角/阴影/组件）
- `docs/Skills安装指南.md`（12 个核心 skills 清单 + 市面分析 + 使用时机）
- `docs/verify-commands.md`（各端验证命令）
- `.env.example`（环境变量模板）
- `.gitignore`

---

## 四、代码要求（硬约束，违反即返工）

### 4.1 命名规约（PRD E1.1）

| 类别 | 规约 | 示例 |
|---|---|---|
| 组件文件 | PascalCase | `ProductCard.tsx` |
| 函数/hook | camelCase | `useProductList` |
| 常量 | UPPER_SNAKE | `MAX_CART_ITEMS` |
| 类型/接口 | PascalCase | `Product`、`OrderItem` |
| 后端 DTO | PascalCase + 后缀 | `ProductCreate`/`ProductResponse` |
| DB 表名 | snake_case 复数 | `orders`、`order_items` |
| DB 字段 | snake_case | `created_at` |
| API 路径 | kebab-case 复数 | `/api/v1/order-items/{id}` |
| CSS 类 | kebab-case + BEM | `product-card__title--active` |
| 枚举值 | UPPER_SNAKE | `PENDING_PAYMENT` |
| Commit | Conventional Commits | `feat(order): add cancel` |

### 4.2 后端代码约束（PRD E1.2）

- **分层**：`api → services → repositories → models`，禁止跨层调用
- **异步**：全 `async def` + `asyncpg` + `aioredis`，禁同步 IO
- **事务**：写操作必须 `async with db.transaction():` 包裹
- **Pydantic**：请求 `XxxCreate/Update/Query`，响应 `XxxResponse`，禁 ORM 直接返回
- **金额**：DB Integer 分，Python Decimal 元，Pydantic 输出 int 分
- **时间**：DB `TIMESTAMPTZ` 存 UTC，API ISO8601 带时区
- **空值**：对象 null，数组 []，字符串 ""
- **异常**：统一 `raise ApiError(code=, i18n_key=, message=, field=)`，禁 `except: pass`
- **日志**：structlog 结构化，必含 `request_id`/`event`/`user_id`

### 4.3 前端代码约束（PRD E1.3）

- 函数组件 + Hooks，禁 class 组件
- Props 必有 `interface XxxProps`，禁 `any`
- 服务端状态 React Query，客户端状态 Zustand，禁 Context 滥用
- 样式：Tailwind 静态类 + CSS 变量动态值，禁动态拼接 class
- **视觉规范：必须遵循 `docs/设计规范.md`，禁硬编码颜色/字号/间距/圆角/阴影值，一律用 `--color-*` / `--font-size-*` / `--spacing-*` / `--radius-*` / `--shadow-*` 等 CSS 变量**
- **设计质量（impeccable skill）**：子 Agent 完成 UI 后，主 Agent 调用 impeccable `/audit` 做设计审查（排版/色彩/间距/对比度/a11y），上线前调 `/polish` 精细化 + `/harden` 生产就绪检查。CI 里跑 `npx impeccable detect` 60 条确定性规则（不调 LLM）。Impeccable 的反模式库（禁 Inter/Arial/紫色渐变/嵌套卡片/弹跳缓动）与项目设计规范互补，在 `.impeccable.md` 里加"优先遵循 docs/设计规范.md，主色 #ff6b6b"
- 金额一律 `number`（分），展示前 `formatPrice()`
- API 调用统一走 `src/api/*` + React Query，禁组件内裸 axios
- 所有展示文本走 i18n key，禁硬编码中文
- 错误处理：拦截器统一处理 ApiError，组件层 toast
- 路由 React Router v6，配置集中 `routes/`
- 大组件 `React.lazy` + Suspense
- 语义化 HTML，禁 `<div onClick>` 模拟交互
- **写操作按钮必须用 `useDebounceAction` Hook（PRD E16.2）**：loading 期间 disabled

### 4.4 公共代码约束

- 公共 API 必须有 TSDoc/docstring 注释（PRD E4.3）
- 共享组件全部 `"use client"`（PRD E2.3），禁 `import.meta.env` / `process.env`
- 低代码组件必含 `version` 字段（PRD D3.1），配合迁移函数

### 4.5 提交与分支（PRD E1.4）

- 分支：`main` + `feat/plan-{i}`
- Commit message：Conventional Commits
- 提交粒度：一个模块/一次验证通过即 commit
- 主 Agent 验收通过后用 AskUserQuestion 请用户合并 main
- 禁子 Agent 自行 `git push` / `git push --force` / `git reset --hard`

---

## 五、验证要求（PRD E1.5、E15）

### 5.1 各端验证命令

| 端 | 验证命令 |
|---|---|
| backend | `cd backend && ruff check . && mypy . && pytest -v --cov=app --cov-report=term-missing` |
| h5-app | `cd packages/h5-app && tsc --noEmit && eslint src --ext .ts,.tsx && pnpm test && pnpm build` |
| admin-app | `cd packages/admin-app && tsc --noEmit && eslint src --ext .ts,.tsx && pnpm test && pnpm build` |
| shared-* | `pnpm build && pnpm test` |
| 集成 | `cd tests/e2e && pnpm playwright test` |

### 5.2 验证规则

- **子 Agent 完成后必须真实运行验证命令**，把真实输出粘进 final summary
- **主 Agent 5 步验收时自己再跑一遍**，数字对得上才算通过
- 禁止通过 `.skip` / 注释断言 / 改测试迎合错误实现
- 验证不通过不得声称完成
- 构建通过 ≠ 功能正确，业务正确性靠单测 + E2E

### 5.3 1a 期验收清单（PRD E15）

主 Agent 在所有 plan 完成后，按 PRD 附录 E15.1/E15.2/E15.3 验收：
- 16 项功能验收
- 11 项非功能验收
- 5 项代码质量验收

---

## 六、安全红线（PRD E11.5）

1. **永不连生产环境**：子 Agent 的 DB/Redis/OSS/支付全指向本地/沙箱
2. **密钥只进 .env**：不得写进代码/AGENTS.md/commit
3. **危险命令需用户批准**：`rm -rf` / `git push --force` / `DROP TABLE` 一律拒绝
4. **支付/鉴权/迁移代码人工 review**：主 Agent 完成后用 AskUserQuestion 请用户 review
5. **不让子 Agent 自行对外发布**：部署/发版/推送镜像全部用户手动
6. **CSRF 防护**：Cookie `SameSite=Lax`，敏感写操作校验 Origin
7. **XSS 防护**：富文本统一走 `DOMPurify` 白名单
8. **JWT**：HS256，access 2h / refresh 7d
9. **bcrypt cost**：12

---

## 七、防抖与幂等（PRD E16，硬约束）

### 7.1 前端防抖

所有写操作按钮必须用 `useDebounceAction` Hook 或等价防抖：

| 按钮类型 | 防抖延迟 | disabled 条件 |
|---|---|---|
| 下单 | 800ms | loading 期间 |
| 支付 | 单次会话内幂等 + loading | paidRef 或 loading |
| 加购 | 300ms | loading |
| 删除 | 500ms | loading |
| 表单提交 | 1000ms | loading |
| 短信验证码 | 倒计时 60s | 倒计时期间 |
| 后台发货/改价 | 500ms | loading |

**禁止**：loading 期间允许重复点击。

### 7.2 后端幂等

所有写操作接口必须实现幂等：

- 请求带 `_requestId`（前端生成）
- 后端用 `(userId, _requestId, action_type)` 作幂等键，存 Redis 5 分钟
- DB 用 `client_request_id` 唯一索引兜底
- 重复请求返回已创建的资源，不重复创建

### 7.3 React Query 写操作

写操作 `useMutation` 必须 `retry: 0`，避免后端创建多条。

---

## 八、主 Agent 调度机制（PRD 工作流文档 v2.0）

### 8.1 主 Agent 职责边界

| 职责 | 做 | 说明 |
|---|---|---|
| 拆计划 | ✅ | 读 PRD v1.3，现场写 `plans/plan-{i}.md` |
| 启动子 Agent | ✅ | Task 工具，`subagent_type=general_purpose_task` |
| 监视子 Agent | ✅ | Task 同步等待返回，无需轮询 |
| 5 步验收 | ✅ | 查改动/跑验证/查幻觉/抽查/类型检查 |
| 决定通过/打回 | ✅ | 通过 → 启动下一个；不通过 → 修复模板重启 |
| 交接信息流 | ✅ | 把 final summary 塞进下个 Task query |
| 写业务代码 | ❌ | 子 Agent 才写 |
| 架构变更 | ❌ | 用 AskUserQuestion 请示用户 |
| git push / 合并 main | ❌ | 用 AskUserQuestion 请示用户 |
| 新依赖引入 | ❌ | 用 AskUserQuestion 请示用户 |

### 8.2 5+1 步验收（决定权实现）

每个子 Agent 返回 final summary 后，主 Agent 必须执行：

1. **查改动范围**：`git status` + `git diff --name-only`，越界则 reject
2. **跑验证命令**：子 Agent 报告的命令，主 Agent 自己再跑一遍
3. **查幻觉依赖**：Grep 查 import，对照 package.json / requirements
4. **抽查 1-2 个文件**：Read 看是否真实实现（非 TODO 空壳）
5. **类型检查/构建**：GetDiagnostics 或跑 tsc/mypy
6. **重复检测**（project-radar skill）：Grep 搜索新代码是否有与 `.codex/project-context.md` 中已有代码重复的组件/函数/类型。发现重复则 reject，提示子 Agent 复用已有代码。检测规则：
   - 组件名重复 → reject，提示"复用已有组件 {file}"
   - 函数名重复 → reject，提示"复用已有函数 {file}"
   - 类型/interface 重复 → reject，提示"从 @liteshop/shared-types 导入"
   - 枚举重复 → reject，提示"从 @liteshop/shared-types/enums 导入"
   - API 路径硬编码重复 → warn，提示"使用已有 api 封装"
   - CSS 硬编码（非 CSS 变量） → warn，提示"用 --color-* / --font-size-* 等"
   - 组件名相似度 > 80% → warn，提示"与已有组件 {name} 相似，考虑合并"

### 8.3 串行调度

主 Agent 一条消息只发一个 Task 调用，等返回再发下一个。**禁止并行**（除非用户明确要求）。

### 8.4 交接信息流

主 Agent 把上个子 Agent 的 final summary 解析后，提取以下 4 项塞进下个 Task query：
- 已完成：上个子 Agent 完成的任务摘要
- 关键决策：为什么这么设计的决策记录
- 给下一个的提示：必须先看的事项、已知坑
- 阻塞项：需要主 Agent/用户决策的未决事项

交接信息控制在 500 字内，只传关键决策和阻塞项，不传完整 final summary。

### 8.5 项目雷达（project-radar skill，通用全局 Skill）

主 Agent 启动后**第一时间**调用 project-radar skill。

**路径说明**：
- **全局安装**：`~/.codex/skills/project-radar/SKILL.md`（用户手动安装，所有项目共用）
- **项目内副本**：`.codex/skills/project-radar/SKILL.md`（作为安装源备份，主 Agent 在第一步初始化时从项目内副本复制到全局）
- **主 Agent 实际读**：全局 `~/.codex/skills/project-radar/SKILL.md`（如果全局不存在，回退读项目内副本）

Skill 执行 **5 步核心流程**：扫描 → 分析 → 提示 → 需求覆盖检查 → 生成。

**5 步核心流程**：
1. **5 层项目识别**：L0 配置文件 → L1 目录结构 → L2 依赖关键词 → L3 PRD 关键词 → L4 代码模式，综合判断项目类型
2. **动态生成配置包**：按识别结果，现场生成项目专属配置包到 `.codex/skills/project-radar/profiles/{type}.md`（不预创建，主 Agent 根据项目实际情况生成）
3. **分析风险**：基础 14 类 + 配置包专属风险（动态加载）+ 条件触发（契约/幂等按项目类型触发）+ 额外自适应检测项（幻觉依赖/CSS 硬编码/构建体积/测试框架/CI 配置）
4. **提示用户**：用 AskUserQuestion 展示风险报告 + 建议调整产品文档/工作流，只建议不擅改
5. **需求覆盖检查**：自适应关键词提取 PRD 需求点（4 组关键词探测，选命中最多的 2 组）→ 自适应任务载体对照（plans/phases/tasks/issues）→ 遗漏则 AskUserQuestion

**生成产物**：`.codex/project-context.md`（6 部分：代码索引 + 分层读指引 + 风险清单 + 工作流适配 + MVP 清单 + 需求覆盖矩阵，全 {占位符} 动态填充）

**运行时机**（5 步核心流程在不同时机的调用）：
- **每个子 Agent 启动前**：读 `project-context.md` 代码索引章节，塞进 Task query
- **每个子 Agent 完成后**：5+1 步验收第 6 步重复检测
- **每 3 个 plan 完成后**：重新扫描，增量更新 `project-context.md` + 上下文压缩
- **验收前**：自适应定位 MVP 清单章节，对照验收清单检查覆盖

**子 Agent 不直接调用此 skill**，由主 Agent 调用后把结果注入 Task query。

#### 8.5.1 project-context.md 内容

project-radar 在项目内生成的 `.codex/project-context.md` 包含 **6 部分**：
- **代码索引**：已有类型/枚举/函数/组件/CSS 变量/API 路由清单（含文件路径），子 Agent 启动前必读
- **PRD 分层读指引**：3 层分层读（主 Agent 启动读目录+MVP 清单+阶段表 → 拆 plan 时读附录章节 → 子 Agent 只读 plan 文件）
- **风险清单 + 已确认的调整**：记录分析出的风险（基础 14 类 + 配置包专属）+ 用户已确认的调整方案
- **Agent 工作流适配建议**：根据项目规模建议串行/并行、plan 数量、上下文预算、子 Agent 前置上下文注入规约
- **完整 MVP 清单**：从 PRD §7.1 提取，验收时逐项检查，如果验收清单项数 < 此清单项数说明验收有遗漏
- **需求覆盖矩阵**：每个 PRD 需求点对应的 plan，确保无遗漏

#### 8.5.2 PRD 分层读指引（3 层）

主 Agent 和子 Agent **禁止一次读全 PRD**（25 万字符会撑爆上下文）。按以下 3 层分层读：

| 层次 | 谁读 | 读什么 | 估算 token | 用途 |
|---|---|---|---|---|
| 第 1 层 | 主 Agent 启动时 | PRD 目录 + §7.1 MVP 清单 + §D8.1 阶段表 | ~1 万 | 拆计划，确保覆盖所有需求 |
| 第 2 层 | 主 Agent 拆每个 plan 时 | plan 对应的 PRD 附录章节（如 plan-05 读 D1.1+E3.1） | ~0.5 万/plan | 把 PRD 需求翻译成 plan 的任务清单 |
| 第 3 层 | 子 Agent 执行时 | 只读 plans/plan-{i}.md（含完整任务清单，主 Agent 已翻译好） | ~0.2 万 | 子 Agent 按 plan 执行，不需读 PRD |

**关键**：主 Agent 拆计划时读第 1 层 + 第 2 层，把 PRD 需求翻译成 plan 的任务清单。子 Agent 只读 plan 文件，plan 文件里有完整的任务清单。

| Plan | PRD 章节 |
|---|---|
| plan-01~03 | D2.4 + E2 + E8.2 |
| plan-04 | D2.1~D2.5 + E3.4 + E7.2 |
| plan-05 | D1.1.1 + D1.5 + E3.1 + E3.2 |
| plan-06 | D1.1 + D1.3.6 + E3.3 + E3.5 + E3.8 + E16 |
| plan-07 | D4.1 + D4.4 + E1.3 |
| plan-08 | PRD 4.1.2 + D6.3 |
| plan-09 | D1.3 + D6.5 + D6.6 + E16 |
| plan-10 | D1.4 + E1.4 + PRD 4.2 |
| plan-11 | D6.2 + E3.8 |
| plan-12 | D6.4 + D6.5 + E5.4 |
| plan-13 | E15 + E3.1.2 + E12 + E16 |

主 Agent 在拆 plan 时，每个 `plans/plan-{i}.md` 顶部写明"PRD 章节：D1.1+E3.1"，子 Agent 只读这些章节。

### 8.6 人工介入红线

主 Agent 遇到以下场景一律用 AskUserQuestion 请示用户：

| 类型 | 场景 |
|---|---|
| 架构决策 | 技术栈变更、服务拆分、DB 表结构大改 |
| 契约变更 | API 字段增删、枚举变更 |
| 资金安全 | 支付、退款、金额计算最终 review |
| 数据安全 | DB 迁移（删列/回填）、生产数据操作 |
| 对外操作 | git push、发版、部署、域名/证书 |
| 依赖决策 | 引入新的重型依赖 |
| 需求取舍 | 某功能做不做、PRD 与实现冲突 |
| 合并决策 | 特性分支合入 main 前的最终 review |

---

## 九、错误码与 i18n（PRD D2.2、D2.3）

错误响应三层结构：

```json
{
  "code": 20303,
  "message": "商品价格已变更，请重新确认",
  "i18nKey": "errors.price_changed",
  "field": "price_cents",
  "details": { "skuId": 123, "oldPrice": 1999, "newPrice": 2099 },
  "requestId": "req_abc123"
}
```

后端默认返回中文 message + i18nKey，前端有翻译则替换。完整错误码表见 `docs/error-codes.md`。

---

## 十、金额规约（PRD D1.2，硬约束）

| 层 | 格式 | 示例 |
|---|---|---|
| PostgreSQL | `INTEGER`（分） | `1999` = ¥19.99 |
| Python | `Decimal`（元），序列化为 int（分） | `Decimal('19.99')` → API `1999` |
| API | `integer`（分） | `"price": 1999` |
| TypeScript | `number`（分） | `const price = 1999` |
| 前端展示 | `formatPrice(1999)` → `"¥19.99"` | — |

---

## 十一、状态机规约（PRD D1.1）

### 11.1 订单正向状态机（orders.status）

5 个状态：`PENDING_PAYMENT → PAID → SHIPPED → COMPLETED`，加 `CANCELLED`。

状态变更用乐观锁：`UPDATE orders SET status=:new WHERE id=:id AND status=:old`，检查影响行数。

### 11.2 售后独立状态机（after_sales.status）

7+1 个状态：`PENDING_REVIEW → APPROVED → GOODS_RETURNED → REFUNDING → REFUNDED`，加 `REJECTED` / `REFUND_FAILED` / `CLOSED`。

### 11.3 库存三层模型（PRD E3.1）

- `physical_stock`：实际库存
- `locked_stock`：锁定库存（已下单未发货）
- `available_stock = physical_stock - locked_stock`（计算字段）

原子操作 SQL（PRD E3.1.2）：
- 下单锁定：`UPDATE skus SET locked_stock = locked_stock + :qty WHERE ... AND (physical_stock - locked_stock) >= :qty`
- 发货扣减：`UPDATE skus SET locked_stock -= :qty, physical_stock -= :qty`
- 取消回滚：`UPDATE skus SET locked_stock -= :qty`
- 售后回滚：`UPDATE skus SET physical_stock += :qty`

---

## 十二、低代码规约（PRD D3、E2）

### 12.1 Schema 版本管理

- `ComponentSchema` 必含 `version` 字段
- 渲染前调用 `migrateComponent(schema)` 迁移到最新
- 迁移函数只增不改，存储保留原版本

### 12.2 组件分层

| 层 | 职责 |
|---|---|
| L4 业务页面 | H5/Admin 路由页 |
| L3 业务组合 | ProductCard + AddToCartButton |
| L2 低代码 | SchemaRenderer / ProductGrid（可被搭建器配置） |
| L1 原子 | Button/Input/Modal（基于 antd-mobile/antd 二次封装） |
| L0 Tokens | CSS 变量 / Tailwind / 主题 |

### 12.3 低代码组件规约

- Schema 驱动：配置项可序列化为 JSON
- 预览态 = 运行态：画布与 H5 用同一组件
- 不引用业务 store：数据通过 props 注入
- 必含 Storybook Story（PRD E2.4）

---

## 十三、配置文件

- `~/.codex/config.toml`：CLI 模式才需要（IDE 模式不用）
- `.env.development`：开发环境配置（可提交 git）
- `.env.staging` / `.env.production`：不提交 git，部署时注入
- `.nvmrc`：`22`
- `runtime.txt`：`3.12`
- `turbo.json`：Monorepo 增量构建配置

---

## 十四、附录引用

本 AGENTS.md 是 PRD v1.3 附录 E1 的执行版本。详细设计见：

- PRD 附录 D1：数据模型（订单/售后/库存/SPU/SKU 等 DDL）
- PRD 附录 D2：接口契约（错误码/i18n/枚举/通知/限流）
- PRD 附录 D3：低代码 Schema 版本与缓存
- PRD 附录 D4：架构与性能（多级缓存/ISR/双构建/3D 隔离）
- PRD 附录 D5：安全合规（表单加密/文件上传/支付环境/a11y）
- PRD 附录 D6：新增功能（通知/评价/搜索/库存预警/运费/优惠券）
- PRD 附录 D7：可观测性 DevOps（监控/SourceMap/蓝绿/CI）
- PRD 附录 D8：范围调整与排期（1a/1b 分阶段）
- PRD 附录 E0：闭环性补强清单
- PRD 附录 E1：代码约束（本文件依据）
- PRD 附录 E2：前端组件化与设计系统
- PRD 附录 E3：完整数据模型补遗
- PRD 附录 E4：代码注释规约
- PRD 附录 E5：行业对照
- PRD 附录 E6/E7/E8/E12/E15/E16：SSE 鉴权/接口契约补强/低代码 Schema 示例/订单超时竞态/1a 期验收清单/防抖幂等
- PRD 附录 E15：1a 期验收清单
- PRD 附录 E16：防抖与幂等双层防护

---

**本文件结束**

> 所有 Agent 必须先读 AGENTS.md，再读 plans/plan-{i}.md。违反任何约束即返工。
