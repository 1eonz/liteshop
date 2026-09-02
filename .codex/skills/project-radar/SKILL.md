# Project Radar Skill

> **Skill 名称**：project-radar
> **性质**：通用 Skill，与项目无关，全局安装一次，所有项目共用
> **安装位置**：`~/.codex/skills/project-radar/SKILL.md`（全局）
> **作用**：在任何项目启动主 Agent 时，先扫描项目全局，分析 16 类风险，**提取完整需求清单并检查覆盖**，提示用户调整产品文档和 Agent 工作流，然后在项目内生成 `.codex/project-context.md` 供该项目的 Agent 使用
> **设计理念**：让 Agent 在动手前先"看清全局"，避免盲目编码、重复造轮子、上下文爆炸、**需求遗漏**

---

## 一、Skill 触发时机

主 Agent 启动后**第一时间**调用此 Skill，在任何编码/拆计划/启动子 Agent 之前执行。

```
主 Agent 启动
  ↓
调用 project-radar skill（5 步：扫描 → 分析 → 提示 → 覆盖检查 → 生成）
  ↓
生成 .codex/project-context.md
  ↓
主 Agent 读 project-context.md，按其中的指引拆计划/调度子 Agent
```

**5 步流程**：
1. 扫描项目（自动识别技术栈/目录结构/已有代码/已有文档）
2. 分析 16 类风险（14 类基础 + 2 类覆盖类）
3. 提示用户（AskUserQuestion 展示风险报告 + 建议调整）
4. **需求覆盖检查**（Grep 提取 PRD 所有需求点 → 对照 plans/ 检查覆盖 → 遗漏则 AskUserQuestion）
5. 生成 `.codex/project-context.md`（含代码索引 + 分层读指引 + 风险清单 + 工作流适配 + 完整 MVP 清单）

---

## 二、第一步：扫描项目（自动识别，不硬编码）

### 2.1 识别技术栈

通过读取项目根目录的配置文件自动识别：

| 配置文件 | 识别出的技术栈 |
|---|---|
| `package.json` | Node.js + 前端框架（React/Vue/Next.js...） |
| `pnpm-workspace.yaml` | Monorepo（pnpm） |
| `requirements.txt` / `pyproject.toml` | Python（FastAPI/Django/Flask...） |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `docker-compose.yml` | 基础设施（PostgreSQL/Redis/MySQL...） |
| `.nvmrc` / `runtime.txt` | 运行时版本 |
| `AGENTS.md` | 已有 Agent 宪法 |
| `turbo.json` | Turborepo |

### 2.2 识别目录结构

扫描项目根目录，识别出：
- Monorepo 还是单包
- 前端目录（`packages/`、`src/`、`app/`...）
- 后端目录（`backend/`、`server/`、`api/`...）
- 共享目录（`shared/`、`packages/shared-*`...）
- 测试目录（`tests/`、`e2e/`...）
- 文档目录（`docs/`...）
- 脚本目录（`scripts/`...）

### 2.3 扫描已有代码

扫描以下类型的导出（如果有）：

**TypeScript/JavaScript 项目**：
- 扫描所有 `*.ts`/`*.tsx` 文件的 `export` 语句
- 提取：类型（interface/type）、枚举（const 对象）、函数、组件、Hooks
- 记录：名称、文件路径、props 签名（组件）、参数签名（函数）

**Python 项目**：
- 扫描所有 `*.py` 文件的 `class`/`def` 定义
- 提取：类、函数、Pydantic 模型
- 记录：名称、文件路径、参数签名

**其他语言**：类似扫描逻辑

### 2.4 识别已有文档

扫描 `docs/` 和根目录，识别：
- PRD/产品需求文档（识别大小，估算 token 数）
- AGENTS.md / .codex/config.toml
- 设计规范 / Design System 文档
- 工作流文档
- OpenAPI 契约
- 错误码表
- 验证命令清单

### 2.5 估算上下文预算

| 文档/代码总量 | 估算 token | 是否需要分层读 |
|---|---|---|
| < 2 万字符 | < 1 万 token | 可一次全读 |
| 2-10 万字符 | 1-5 万 token | 建议分层读 |
| > 10 万字符 | > 5 万 token | **必须分层读** |

---

## 三、第二步：分析 16 类风险

### 3.1 基础风险（14 类）

| # | 风险 | 检测方式 | 严重度 |
|---|---|---|---|
| 1 | 上下文爆炸 | 文档总 token 估算 > 主模型上下文窗口的 60% | 🔴 |
| 2 | 重复造轮子（组件） | 子 Agent 是 stateless，不知道已有组件 | 🔴 |
| 3 | 重复定义类型 | 子 Agent 不知道 shared-types 已有什么 | 🔴 |
| 4 | 重复实现函数 | 子 Agent 不知道已有工具函数 | 🟡 |
| 5 | 参数/类型不一致 | 前后端命名/格式/枚举不一致 | 🔴 |
| 6 | 子 Agent 盲目编码 | 子 Agent 不知道该读哪些文件 | 🟡 |
| 7 | 类似逻辑重复 | 多个子 Agent 实现相似逻辑 | 🟡 |
| 8 | 上下文烧钱 | 重复读大文件、不压缩历史 | 🟡 |
| 9 | 契约缺失 | 没有 OpenAPI 契约就启动子 Agent | 🔴 |
| 10 | 领地隔离失效 | 没有 AGENTS.md 或领地约束不明确 | 🔴 |
| 11 | 依赖未装 | node_modules/.venv 不存在 | 🟡 |
| 12 | 基础设施未启动 | docker-compose 没启动 PostgreSQL/Redis | 🟡 |
| 13 | 幂等缺失 | 写操作接口没有幂等设计（`_requestId`） | 🔴 |
| 14 | a11y 合规 | 没有 a11y 检查机制 | 🟡 |

### 3.2 覆盖类风险（2 类，新增）

| # | 风险 | 检测方式 | 严重度 |
|---|---|---|---|
| 15 | **需求遗漏** | PRD 里的需求点没有对应 plan | 🔴 |
| 16 | **验收遗漏** | PRD 的 MVP 清单项数 > 验收清单项数 | 🔴 |

### 3.3 额外检测项（根据项目类型自动适配）

| 检测项 | 适用 | 说明 |
|---|---|---|
| 状态机竞态 | 电商/订单系统 | 订单超时 vs 支付回调并发 |
| 防抖缺失 | 前端按钮 | 写操作按钮没有防抖 |
| CSS 硬编码 | 前端项目 | 颜色/字号/间距没有用 CSS 变量 |
| 幻觉依赖风险 | 所有项目 | 子 Agent 可能 import 不存在的库 |
| 构建产物体积 | 前端项目 | 首屏 JS gzip 是否超限 |
| 数据库迁移可逆 | 后端项目 | Alembic/Prisma 是否有 downgrade |

---

## 四、第三步：提示用户（AskUserQuestion）

### 4.1 风险报告

Skill 分析完后，用 AskUserQuestion 向用户展示风险报告：

```
project-radar 扫描完成，发现以下问题：

🔴 高风险（3 项）：
1. 上下文爆炸：PRD 25 万字符（约 12 万 token），主 Agent 全读会撑爆
   建议：分层读，主 Agent 只读目录+MVP 清单+阶段表，子 Agent 只读 plan 文件
2. 契约缺失：没有 OpenAPI 契约
   建议：先做阶段 0 契约先行
3. 幂等缺失：写操作接口没有幂等设计
   建议：加 _requestId 幂等机制

🟡 中风险（2 项）：
4. 重复造轮子：子 Agent stateless，不知道已有组件
   建议：生成代码索引，子 Agent 启动前注入
5. 依赖未装：node_modules 不存在
   建议：先跑 pnpm install

是否按建议调整？
```

### 4.2 逐项确认

用户逐项确认是否调整：

| 风险 | 用户选项 |
|---|---|
| 上下文爆炸 | "按建议分层读" / "不改，我手动处理" / "跳过" |
| 契约缺失 | "先做契约先行" / "跳过，直接编码" |
| 幂等缺失 | "加幂等机制" / "跳过" |
| 重复造轮子 | "生成代码索引" / "跳过" |
| 依赖未装 | "现在装" / "跳过" |
| ... | ... |

### 4.3 产品文档/工作流调整建议

如果 Skill 发现产品文档或 Agent 工作流有问题，会建议调整：

```
project-radar 发现 Agent 工作流有以下问题：

1. AGENTS.md 没有领地隔离规则
   建议：加入领地约束表（哪些 Agent 只能改哪些目录）
   是否调整？

2. 工作流文档没有 5+1 步验收机制
   建议：加入 5+1 步验收（含重复检测）
   是否调整？

3. PRD 没有分层读指引
   建议：为每个 plan 标注 PRD 章节
   是否调整？
```

用户确认后，Skill 修改对应文档（AGENTS.md / 工作流文档 / PRD plan 模板）。

**重要**：Skill **只建议，不擅自修改**。每次修改前都用 AskUserQuestion 确认。

---

## 五、第四步：需求覆盖检查（防止需求遗漏）

### 5.1 为什么需要这一步

主 Agent 只读 PRD 摘要（目录 + MVP 清单 + 阶段表），可能遗漏细节需求。例如：
- PRD 4.1.3 提到"购物车动画（抛物线飞入）"，但 D8.1 阶段表只写了"购物车"
- PRD 4.1.6 提到"微信授权登录"，但 D8.1 只写了"用户认证"
- PRD 4.2.10 提到"商城主题配置"，但 D8.1 只写了"系统设置"

**如果只读摘要，这些细节需求会被遗漏。**

### 5.2 检查流程

```
① Grep 提取 PRD 所有需求点
   搜索关键词："- [ ]" / "功能点" / "P0" / "必须实现" / "一期" / "| 功能点 |"
   提取出所有需求点，如：
   - 手机号+短信验证码登录
   - 微信授权登录（H5 环境下 OAuth）
   - 首页（低代码 Schema 渲染）
   - 购物车动画（抛物线飞入）
   - 商城主题配置（主色/导航栏/Tabbar）
   - ...

② 对照 plans/ 检查覆盖
   for each 需求点 in PRD:
       在 plans/INDEX.md 和所有 plan-*.md 文件里 Grep 搜索
       if 没有对应 plan 且没有对应任务清单项:
           遗漏清单.append(需求点)

③ 提示用户
   AskUserQuestion:
   "project-radar 需求覆盖检查发现以下需求未拆到 plan：
    - 购物车动画（抛物线飞入）— PRD 4.1.3
    - 微信授权登录 — PRD 4.1.6
    - 浏览足迹 — PRD 4.1.5
    - 商城主题配置 — PRD 4.2.10
    是否补拆 plan 或加到已有 plan 的任务清单？"

④ 用户确认后补拆
   用户确认后，主 Agent 补拆对应 plan，或把遗漏需求加到已有 plan 的任务清单里
```

### 5.3 检查规则

| 检查项 | 规则 | 处理 |
|---|---|---|
| 需求点无对应 plan | PRD 里的需求点在 plans/ 里搜不到 | AskUserQuestion 提示 |
| 需求点有 plan 但无任务清单项 | plan 文件里没有该需求的具体任务 | AskUserQuestion 提示 |
| MVP 清单项数 vs 验收清单项数 | PRD 的 MVP 清单（如 49 项）> 验收清单（如 32 项） | AskUserQuestion 提示"验收清单可能遗漏" |

### 5.4 验收覆盖检查

在所有 plan 完成后、进入验收阶段前，再做一次覆盖检查：

```
① Grep 提取 PRD 的 MVP 必须实现清单（通常是 §7.1 或类似章节）
② 对照验收清单（如 PRD §E15）逐项检查
③ 发现 MVP 清单有但验收清单没有的项 → AskUserQuestion 提示"以下 MVP 项未列入验收"
④ 用户确认后补充验收项
```

---

## 六、第五步：生成 .codex/project-context.md

Skill 在项目根目录的 `.codex/` 下生成 `project-context.md`，包含 **6 个部分**：

### 6.1 代码索引（已有类型/组件/函数清单）

```markdown
## 代码索引

> 最后更新：{时间戳}（{plan 名称}完成后）
> 由 project-radar skill 自动生成，子 Agent 启动前必读

### shared-types 导出清单
（类型/枚举/工具函数清单，含文件路径）

### shared-components 导出清单
（组件清单，含 props 签名）

### backend 导出清单
（API 路由/Services/Models 清单）

### 前端导出清单
（API 封装/业务组件/页面清单）
```

### 6.2 PRD 分层读指引（不是"只读摘要"，是"分层读"）

```markdown
## PRD 分层读指引

> PRD 总体积：25 万字符（约 12 万 token）
> 禁止一次读全 PRD，按以下 3 层分层读

### 第 1 层：主 Agent 启动时读（拆计划用）
- PRD 目录（了解整体结构）
- PRD §7.1 MVP 必须实现清单（确保覆盖所有需求）
- PRD §D8.1 阶段表（了解 plan 拆分顺序）
- 估算 token：~1 万

### 第 2 层：主 Agent 拆每个 plan 时读（翻译需求为任务清单）
- plan 对应的 PRD 附录章节（如 plan-05 读 D1.1+E3.1）
- 主 Agent 把 PRD 需求翻译成 plan 的任务清单
- 估算 token：~0.5 万/plan

### 第 3 层：子 Agent 执行时读（只读 plan 文件，不需读 PRD）
- 只读 plans/plan-{i}.md（含完整任务清单，主 Agent 已翻译好）
- 子 Agent 不需读 PRD，plan 文件里有完整的任务清单
- 估算 token：~0.2 万

### PRD 章节对照表
| Plan | PRD 章节 | 说明 |
|---|---|---|
| plan-01 | 第 3 章 + 附录 D2.4 | 枚举管理 |
| plan-02 | 附录 D1.1 + E3.1 | 订单状态机 + 库存 |
| ... | ... | ... |
```

### 6.3 风险清单 + 已确认的调整

```markdown
## 风险清单

### 已确认调整（用户已同意）
1. ✅ PRD 分层读（已生成上表）
2. ✅ 生成代码索引（已生成上方）
3. ✅ 加幂等机制（AGENTS.md 已更新）
4. ✅ 需求覆盖检查（已补拆 3 个遗漏需求到 plan）

### 未处理（用户选择跳过）
5. ⏭️ a11y 检查（用户选择跳过，二期再做）
```

### 6.4 Agent 工作流适配建议

```markdown
## Agent 工作流适配建议

### 项目规模
- 文档总量：25 万字符
- 预计 plan 数量：13 个
- 建议调度模式：串行（主 Agent 上下文压力大）
- 上下文预算：8-10 万 token（分层读 + 压缩后）

### 子 Agent 前置上下文注入
主 Agent 启动子 Agent 时，Task query 里塞入：
1. 本文档的"代码索引"相关章节摘要（约 500-1000 字）
2. 子 Agent 可能依赖的已有导出清单
3. PRD 分层读指引（只读相关章节）
4. 上个子 Agent 的交接信息

### 5+1 步验收（含重复检测）
1. 查改动范围（git diff）
2. 跑验证命令
3. 查幻觉依赖（Grep import）
4. 抽查文件（Read）
5. 类型检查（tsc/mypy）
6. 重复检测（Grep 搜索新代码 vs 代码索引）

### 上下文压缩
每 3 个 plan 完成后压缩，丢弃已完成 plan 的 final summary 全文，只保留关键决策。
```

### 6.5 完整 MVP 清单（验收对照用）

```markdown
## 完整 MVP 清单（验收对照用）

> 从 PRD §7.1 提取，验收时逐项检查
> 如果验收清单项数 < 此清单项数，说明验收有遗漏

### H5 商城端（13 项）
1. 手机号+短信验证码登录
2. 微信授权登录（H5 OAuth）
3. 首页（低代码 Schema 渲染）
4. 商品分类页
5. 商品列表页
6. 商品详情页
7. SKU 选择弹窗
8. 购物车（增删改查、全选、合计）
9. 购物车动画（抛物线飞入）
10. 订单确认、提交订单
11. 微信支付 + 支付宝
12. 订单列表、订单详情
13. 收货地址管理

### 管理后台（11 项）
...

### 低代码搭建平台（13 项）
...

### 后端（12 项）
...

### 验收清单对照
| MVP 项 | 验收清单对应项 | 是否覆盖 |
|---|---|---|
| 手机号+短信验证码登录 | E15.1 #1 用户注册登录 | ✅ |
| 微信授权登录 | （无） | ❌ 遗漏！ |
| 购物车动画 | （无） | ❌ 遗漏！ |
| ... | ... | ... |
```

### 6.6 需求覆盖矩阵（plan × 需求点）

```markdown
## 需求覆盖矩阵

> 每个 PRD 需求点对应的 plan，确保无遗漏

| PRD 需求点 | PRD 章节 | 对应 plan | 是否覆盖 |
|---|---|---|---|
| 手机号+短信验证码登录 | 4.1.6 | plan-04 | ✅ |
| 微信授权登录 | 4.1.6 | plan-04 | ✅（补拆后） |
| 购物车动画 | 4.1.3 | plan-09 | ✅（补拆后） |
| 商城主题配置 | 4.2.10 | plan-12 | ✅（补拆后） |
| ... | ... | ... | ... |
```

---

## 七、Skill 调用方式

### 7.1 主 Agent 启动时

```
主 Agent 启动后第一条指令：
"调用 project-radar skill，扫描项目，分析风险，提示用户调整，检查需求覆盖，生成 .codex/project-context.md"
```

### 7.2 主 Agent 拆计划后

```
主 Agent 拆完 plans/ 后：
"调用 project-radar 的需求覆盖检查，Grep PRD 提取所有需求点，对照 plans/ 检查覆盖，遗漏则 AskUserQuestion"
```

### 7.3 子 Agent 启动前

主 Agent 读 `project-context.md` 的代码索引章节，把相关摘要塞进子 Agent 的 Task query。

### 7.4 子 Agent 完成后

主 Agent 读 `project-context.md` 的代码索引，Grep 搜索新代码是否有重复，发现重复则 reject。

### 7.5 验收前

```
主 Agent 进入验收阶段前：
"调用 project-radar 的验收覆盖检查，Grep PRD §7.1 MVP 清单，对照验收清单检查覆盖，遗漏则 AskUserQuestion"
```

### 7.6 定期更新

每完成 3 个 plan 后，主 Agent 重新调用 project-radar 扫描更新的目录，增量更新 `project-context.md` 的代码索引和需求覆盖矩阵。

---

## 八、通用性

此 Skill **不绑定任何项目**：

- **技术栈识别**：通过配置文件自动识别，不硬编码
- **目录结构识别**：通过扫描自动识别，不硬编码
- **代码扫描**：按语言自动适配（TS/Python/Go/Rust...）
- **风险分析**：16 类风险通用，额外检测项按项目类型自动适配
- **需求覆盖检查**：Grep PRD 的 `- [ ]` / `功能点` / `P0` / `必须实现` 等关键词，适配任何 PRD 格式
- **文档调整建议**：基于扫描结果生成，不硬编码
- **project-context.md**：每个项目独立生成，内容随项目而异

**任何项目**——电商/SaaS/工具/游戏/IoT——都能用这个 Skill，它会自动适配。

---

## 九、安装方式

### 9.1 全局安装（一次性）

```bash
# 把本 SKILL.md 放到全局目录
mkdir -p ~/.codex/skills/project-radar
cp SKILL.md ~/.codex/skills/project-radar/SKILL.md
```

或通过 CodeX IDE 对话创建：

```
帮我创建一个全局 skill，名为 project-radar，功能是扫描项目全局+分析 16 类风险+提示用户调整+检查需求覆盖+生成 project-context.md
```

### 9.2 验证安装

在 CodeX 聊天窗输入：

```
$list-skills
```

应看到 `project-radar`。

### 9.3 在新项目里使用

打开任何项目 → 启动主 Agent → 主 Agent 自动调用 project-radar → 扫描 → 分析 → 提示 → **覆盖检查** → 生成 `.codex/project-context.md`。

---

## 十、与项目文档的关系

| 文件 | 性质 | 谁生成 | 作用 |
|---|---|---|---|
| `~/.codex/skills/project-radar/SKILL.md` | **通用** | 用户手动安装 | 装一次，所有项目共用 |
| `{项目}/.codex/project-context.md` | **项目专属** | Skill 在该项目里生成 | 该项目的 Agent 读这份（含代码索引/分层读指引/风险清单/工作流适配/MVP 清单/覆盖矩阵） |
| `{项目}/AGENTS.md` | **项目专属** | Skill 建议调整，用户确认后改 | 该项目的 Agent 宪法 |
| `{项目}/docs/PRD-*.md` | **项目专属** | Skill 建议分层读指引，用户确认后改 | 产品需求 |
| `{项目}/docs/工作流文档.md` | **项目专属** | Skill 建议调整，用户确认后改 | Agent 调度机制 |
| `{项目}/plans/plan-*.md` | **项目专属** | 主 Agent 拆计划时生成，project-radar 检查覆盖 | 子 Agent 的任务清单 |

---

**Skill 结束**

> project-radar 是通用项目雷达，装一次，所有项目共用。它让每个项目的 Agent 在动手前先看清全局，避免盲目编码、重复造轮子、上下文爆炸、**需求遗漏**。
> 每个项目里生成的 `.codex/project-context.md` 是项目专属的 Agent 使用文档，含 6 部分：代码索引 + 分层读指引 + 风险清单 + 工作流适配 + 完整 MVP 清单 + 需求覆盖矩阵。
