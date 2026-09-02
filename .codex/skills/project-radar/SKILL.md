# Project Radar Skill

> **Skill 名称**：project-radar
> **性质**：通用 Skill，与项目无关，全局安装一次，所有项目共用
> **安装位置**：`~/.codex/skills/project-radar/SKILL.md`（仅此一个文件，通用引擎）
> **设计理念**：主 Agent 启动后读 Skill → 5 层识别项目类型 → **动态生成**项目专属配置包到 `.codex/skills/project-radar/profiles/` → 按配置执行。Skill 是"引擎"，配置包是主 Agent 跑的时候**现场生成**的，不预创建。
> **核心原则**：**零硬编码**——SKILL.md 只含通用引擎逻辑和配置包的生成格式定义。所有项目专属假设（电商/教育/BaaS/跨端/小程序）由主 Agent 在项目里动态生成配置包注入。

---

## 一、Skill 架构

```
~/.codex/skills/project-radar/
├── SKILL.md              # 主逻辑（通用引擎，零项目假设）
└── profiles/             # 项目类型配置包（插件）
    ├── ecommerce.md      # 电商：状态机/防抖/幂等/迁移可逆
    ├── education.md      # 教育：版权素材/配额逻辑/自评逻辑
    ├── baas.md           # BaaS：RLS 权限/安全规则
    ├── crossplatform.md  # 跨端：多端 API 兼容/条件编译/包体积
    ├── miniprogram.md    # 小程序：包体积/类目合规
    ├── saas.md           # SaaS：多租户/权限矩阵
    └── i18n.md           # 国际化：key 遗漏
```

**引擎职责**：扫描→识别→加载配置包→分析→提示→覆盖检查→生成
**配置包职责**：定义该类型项目的专属关键词/风险检测项/PRD 格式/任务载体/目录结构

---

## 二、5 步工作流程

```
主 Agent 启动
  ↓
① 扫描项目（5 层识别：配置文件/目录结构/依赖关键词/PRD 关键词/代码模式）
  ↓
② 分析风险（基础 14 类 + 配置包专属风险 + 额外自适应检测项）
  ↓
③ 提示用户（AskUserQuestion 展示风险报告 + 建议调整，只建议不擅改）
  ↓
④ 需求覆盖检查（自适应关键词提取 → 自适应任务载体对照 → 遗漏则 AskUserQuestion）
  ↓
⑤ 生成 .codex/project-context.md（6 部分，全 {占位符} 动态填充）
```

---

## 三、第一步：5 层项目识别

### 3.1 L0 技术栈识别

通过读取项目根目录的配置文件自动识别：

| 配置文件 | 识别出的技术栈 |
|---|---|
| `package.json` | Node.js + 前端框架 |
| `pnpm-workspace.yaml` | Monorepo（pnpm） |
| `requirements.txt` / `pyproject.toml` | Python |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `docker-compose.yml` | 基础设施 |
| `.nvmrc` / `runtime.txt` | 运行时版本 |
| `turbo.json` | Turborepo |

### 3.2 L1 目录结构识别

```
扫描根目录：
- 如果有 pnpm-workspace.yaml / turbo.json / lerna.json
  → monorepo 模式 → 按包扫描（packages/shared-* / packages/h5-app / ...）
- 如果根目录下有多个子项目，各有 package.json / requirements.txt
  → 多项目模式 → 每个子项目独立生成索引
- 如果只有 src/ 或 app/
  → 单项目模式 → 按层级扫描（src/components / src/services / src/types / ...）
```

### 3.3 L2 依赖关键词识别

```
扫描 package.json / requirements.txt / go.mod / Cargo.toml 的依赖列表：
- @tarojs/* → 跨端项目（Taro）
- uni-* → 跨端项目（uni-app）
- react-native → 跨端项目（RN）
- supabase → BaaS 项目（Supabase）
- firebase → BaaS 项目（Firebase）
- appwrite → BaaS 项目（Appwrite）
- @aws-sdk / aws-amplify → AWS BaaS
- next.js → SSR/SSG 项目
- express / fastify / fastapi / django → 有自研后端
- playwright / puppeteer → 有 E2E 测试
- jest / vitest / pytest / go test → 有单元测试框架
```

### 3.4 L3 PRD 关键词识别

```
扫描 PRD / 产品文档：
- 有"订单/支付/购物车/商品/SKU/库存" → 电商领域
- 有"课程/学习/考试/教学/学生/老师" → 教育领域
- 有"租户/多租户/订阅/计费/SaaS" → SaaS 领域
- 有"游戏/玩家/关卡/战斗/背包" → 游戏领域
- 有"设备/IoT/传感器/MQTT/Modbus" → IoT 领域
```

### 3.5 L4 已有代码模式识别

```
扫描已有代码文件名/目录名：
- 有 orders.py / cart.ts / payment.py → 已实现电商功能
- 有 courses/ / lessons/ / exams/ → 已实现教育功能
- 有 supabase/ 目录 → 已用 BaaS
- 有 miniprogram/ 或 app.json(微信) → 小程序
```

### 3.6 综合判断 + 加载配置包

5 层识别后，综合判断项目类型，加载对应配置包：

```
if L2 有 @tarojs/* 或 react-native → 加载 crossplatform.md
if L2 有 supabase/firebase/appwrite → 加载 baas.md
if L3 有电商关键词 → 加载 ecommerce.md
if L3 有教育关键词 → 加载 education.md
if L4 有 miniprogram 或 app.json → 加载 miniprogram.md
if L3 有 SaaS 关键词 → 加载 saas.md
if 有 i18n 目录或 locale 文件 → 加载 i18n.md
```

**可同时加载多个配置包**（如电商 + 跨端 + i18n）。

---

## 四、第二步：分析风险（基础 + 配置包专属）

### 4.1 基础风险（14 类，所有项目通用）

| # | 风险 | 检测方式 | 严重度 |
|---|---|---|---|
| 1 | 上下文爆炸 | 文档总 token 估算 > 主模型上下文窗口的 60% | 🔴 |
| 2 | 重复造轮子（组件） | 子 Agent 是 stateless，不知道已有组件 | 🔴 |
| 3 | 重复定义类型 | 子 Agent 不知道已有类型 | 🔴 |
| 4 | 重复实现函数 | 子 Agent 不知道已有工具函数 | 🟡 |
| 5 | 参数/类型不一致 | 前后端命名/格式/枚举不一致 | 🔴 |
| 6 | 子 Agent 盲目编码 | 子 Agent 不知道该读哪些文件 | 🟡 |
| 7 | 类似逻辑重复 | 多个子 Agent 实现相似逻辑 | 🟡 |
| 8 | 上下文烧钱 | 重复读大文件、不压缩历史 | 🟡 |
| 9 | 契约缺失 | **按项目类型条件触发**（见下） | 🔴 |
| 10 | 领地隔离失效 | 没有 AGENTS.md 或领地约束不明确 | 🔴 |
| 11 | 依赖未装 | node_modules/.venv 不存在 | 🟡 |
| 12 | 基础设施未启动 | docker-compose 没启动 | 🟡 |
| 13 | 幂等缺失 | **按项目类型条件触发**（见下） | 🔴 |
| 14 | a11y 合规 | 没有 a11y 检查机制 | 🟡 |

### 4.2 条件触发的风险（#9 契约 / #13 幂等）

```
#9 契约缺失：
if 项目有自研后端（L2 有 express/fastapi/django）:
    检测 OpenAPI 契约是否存在 → 不存在 → 🔴
else if 项目用 BaaS（L2 有 supabase/firebase）:
    检测 BaaS schema/RLS 配置 → 不存在 → 🟡
else:
    跳过（纯前端/CLI 工具无后端）

#13 幂等缺失：
if 项目有自研后端写操作 API:
    检测 _requestId 幂等设计 → 不存在 → 🔴
else if 项目用 BaaS:
    跳过（BaaS 自带事务和幂等）
else:
    跳过
```

### 4.3 配置包专属风险（动态加载）

每个配置包定义该类型项目的专属风险检测项。例如：

**ecommerce.md**：
```
| 状态机竞态 | 订单超时 vs 支付回调并发 |
| 防抖缺失 | 写操作按钮没有防抖 |
| 数据库迁移可逆 | Alembic/Prisma 是否有 downgrade |
```

**education.md**：
```
| 版权素材误用 | 是否引用了 TED/BBC 等版权素材 |
| 配额逻辑 | 配额限制是否正确（如 2 篇/天）|
| 自评模式逻辑 | 自评三档是否正确 |
```

**baas.md**：
```
| RLS 权限配置 | Supabase RLS 策略是否配置 |
| 安全规则 | Firebase Security Rules 是否配置 |
```

**crossplatform.md**：
```
| 多端 API 兼容 | 是否用了某端专有 API |
| 条件编译 | 跨端条件编译是否正确 |
| 包体积超限 | 小程序包体积是否超限 |
```

### 4.4 额外自适应检测项（所有项目通用）

| 检测项 | 检测方式 |
|---|---|
| 幻觉依赖风险 | 子 Agent 可能 import 不存在的库 |
| CSS 硬编码 | 颜色/字号/间距没有用 CSS 变量 |
| 构建产物体积 | 首屏 JS gzip 是否超限 |
| 测试框架缺失 | 没有 jest/vitest/pytest → 提示安装 |
| CI 配置缺失 | 没有 .github/workflows / .gitlab-ci.yml → 建议添加 |

---

## 五、第三步：提示用户（AskUserQuestion）

### 5.1 风险报告（动态生成，零硬编码示例）

Skill 分析完后，用 AskUserQuestion 向用户展示**动态生成**的风险报告：

```
project-radar 扫描完成，识别项目类型：{电商 + 跨端}

🔴 高风险（{N} 项）：
1. {风险名}：{检测到的具体情况}
   建议：{对应建议}
2. ...

🟡 中风险（{N} 项）：
3. {风险名}：{检测到的具体情况}
   建议：{对应建议}

是否按建议调整？
```

**不硬编码任何示例**——风险报告完全基于扫描结果动态生成。

### 5.2 逐项确认

用户逐项确认是否调整。**只建议，不擅自修改**。

### 5.3 产品文档/工作流调整建议

如果 Skill 发现产品文档或 Agent 工作流有问题，建议调整：

```
project-radar 发现 Agent 工作流有以下问题：

1. {问题}：{具体情况}
   建议：{对应建议}
   是否调整？
```

用户确认后，Skill 修改对应文档。**每次修改前都用 AskUserQuestion 确认**。

---

## 六、第四步：需求覆盖检查（自适应关键词 + 自适应任务载体）

### 6.1 自适应 PRD 格式探测

**不硬编码关键词**，改为两阶段自适应：

```
阶段 1：PRD 格式探测（前 10 秒）
- Grep 多组关键词，统计命中数
- 关键词组 A（checklist 类）："- [ ]" / "- [x]" / "功能点" / "P0" / "必须实现"
- 关键词组 B（版本标注类）："v1.0" / "v1.5" / "v2.0" / "MVP" / "一期" / "二期"
- 关键词组 C（模块编号类）："M1" / "M2" / "模块" / "Module" / "系统"
- 关键词组 D（验收类）："✅" / "❌" / "验收" / "主路径" / "AC" / "Acceptance" / "DoD"
- 选命中数最多的 2 组作为该项目的关键词

阶段 2：用自适应关键词提取需求点
```

### 6.2 自适应任务载体识别

**不硬编码 `plans/` 目录**，改为自动识别：

```
扫描以下位置，自动识别任务载体：
1. plans/plan-*.md           → 命中则用 plans 模式
2. phases/phase-*.md          → 命中则用 phases 模式
3. docs/tasks/*.md            → 命中则用 tasks 模式
4. .github/issues/*.md        → 命中则用 issues 模式
5. 都没有                     → 提示用户"未发现任务载体，建议创建 plans/ 目录"
```

需求覆盖检查时根据识别到的载体模式去对照。

### 6.3 覆盖检查流程

```
① 用自适应关键词提取 PRD 所有需求点

② 用自适应任务载体对照检查
   for each 需求点 in PRD:
       在识别到的任务载体文件里 Grep 搜索
       if 没有对应任务:
           遗漏清单.append(需求点)

③ 提示用户
   AskUserQuestion: "以下需求未拆到任务，是否补拆？"

④ 用户确认后补拆
```

### 6.4 自适应 MVP 清单定位

**不硬编码 §7.1**，改为自适应搜索：

```
搜索以下关键词，定位 MVP 清单章节：
- "MVP" / "必须实现" / "验收标准" / "DoD" / "Definition of Done"
- "主路径" / "核心流程" / "P0 功能" / "v1.0"
- 找到后记录章节号，用于验收覆盖检查
```

### 6.5 验收覆盖检查

```
① 用自适应关键词定位 MVP 清单章节
② Grep 提取 MVP 清单所有项
③ 对照验收清单逐项检查
④ 发现 MVP 清单有但验收清单没有的项 → AskUserQuestion
⑤ 用户确认后补充验收项
```

---

## 七、第五步：生成 .codex/project-context.md（6 部分，全占位符）

Skill 在项目根目录的 `.codex/` 下生成 `project-context.md`，**所有内容用 {占位符} 动态填充**，不出现任何项目专属硬编码。

### 7.1 代码索引（自适应目录结构）

```markdown
## 代码索引

> 最后更新：{时间戳}（{任务名}完成后）
> 由 project-radar skill 自动生成，子 Agent 启动前必读
> 项目结构模式：{monorepo / 多项目 / 单项目}

### {自动识别的模块名 1} 导出清单
（{自动扫描的类型/枚举/函数/组件清单，含文件路径}）

### {自动识别的模块名 2} 导出清单
（...）
```

**目录结构自适应**：
- monorepo → 按包扫描（packages/shared-*/packages/h5-app/...）
- 多项目 → 每个子项目独立生成索引
- 单项目 → 按层级扫描（src/components/src/services/src/types/...）

### 7.2 PRD 分层读指引（全模板化）

```markdown
## PRD 分层读指引

> PRD 总体积：{自动估算} 字符（约 {自动估算} 万 token）
> 禁止一次读全 PRD，按以下 3 层分层读

### 第 1 层：主 Agent 启动时读（拆计划用）
- PRD 目录（了解整体结构）
- PRD {自适应定位的 MVP 清单章节号}（确保覆盖所有需求）
- PRD {自适应定位的阶段表章节号}（了解任务拆分顺序）
- 估算 token：~{自动估算}

### 第 2 层：主 Agent 拆每个任务时读
- 任务对应的 PRD 章节（由主 Agent 拆计划时标注）
- 主 Agent 把 PRD 需求翻译成任务的完整清单
- 估算 token：~{自动估算}/任务

### 第 3 层：子 Agent 执行时读
- 只读 {自适应识别的任务载体路径}（含完整任务清单）
- 子 Agent 不需读 PRD
- 估算 token：~{自动估算}

### PRD 章节对照表
> 由主 Agent 拆计划时动态填写，Skill 不预填

| {任务名} | PRD 章节 | 说明 |
|---|---|---|
| {动态生成} | {动态生成} | {动态生成} |
```

### 7.3 风险清单 + 已确认的调整

```markdown
## 风险清单

### 已确认调整（用户已同意）
1. ✅ {调整项 1}
2. ✅ {调整项 2}

### 未处理（用户选择跳过）
3. ⏭️ {跳过项}
```

### 7.4 Agent 工作流适配建议

```markdown
## Agent 工作流适配建议

### 项目规模
- 文档总量：{自动估算}
- 预计任务数量：{自动估算}
- 建议调度模式：{串行/并行}（{原因}）
- 上下文预算：{自动估算}（分层读 + 压缩后）

### 子 Agent 前置上下文注入
主 Agent 启动子 Agent 时，Task query 里塞入：
1. 本文档的"代码索引"相关章节摘要
2. 子 Agent 可能依赖的已有导出清单
3. PRD 分层读指引
4. 上个子 Agent 的交接信息

### 5+1 步验收（含重复检测）
1. 查改动范围
2. 跑验证命令（{自适应识别的测试框架}）
3. 查幻觉依赖
4. 抽查文件
5. 类型检查（{自适应识别的类型检查工具}）
6. 重复检测

### 上下文压缩
每 3 个任务完成后压缩。
```

### 7.5 完整 MVP 清单（全占位符）

```markdown
## 完整 MVP 清单（验收对照用）

> 从 PRD {自适应定位的章节号} 提取，验收时逐项检查
> 如果验收清单项数 < 此清单项数，说明验收有遗漏

### {自动识别的模块名 1}（{N} 项）
1. {需求点 1}
2. {需求点 2}
...

### 验收清单对照
| MVP 项 | 验收清单对应项 | 是否覆盖 |
|---|---|---|
| {需求点 1} | {验收项 or "（无）❌ 遗漏"} | ✅/❌ |
```

### 7.6 需求覆盖矩阵（全占位符）

```markdown
## 需求覆盖矩阵

> 每个 PRD 需求点对应的任务，确保无遗漏

| PRD 需求点 | PRD 章节 | 对应任务 | 是否覆盖 |
|---|---|---|---|
| {需求点 1} | {章节号} | {任务名} | ✅ |
| {需求点 2} | {章节号} | {任务名 or "（无）❌"} | ✅/❌ |
```

---

## 八、Skill 调用时机

| 时机 | 做什么 |
|---|---|
| 主 Agent 启动后第一时间 | 5 步全流程（扫描→分析→提示→覆盖检查→生成） |
| 主 Agent 拆任务后 | 需求覆盖检查（自适应关键词 + 自适应任务载体） |
| 每个子 Agent 启动前 | 读 project-context.md 代码索引，塞进 Task query |
| 每个子 Agent 完成后 | 5+1 步验收第 6 步重复检测 |
| 每 3 个任务完成后 | 重新扫描，增量更新 project-context.md + 上下文压缩 |
| 验收前 | 验收覆盖检查（自适应 MVP 定位 + 对照验收清单） |
| 上下文接近上限时 | 主动压缩，AskUserQuestion 提示用户 |

---

## 九、通用性保证

此 Skill **零项目假设**：

| 维度 | 通用机制 |
|---|---|
| 技术栈识别 | 5 层识别（配置文件/目录结构/依赖关键词/PRD 关键词/代码模式） |
| 目录结构 | 自适应（monorepo/多项目/单项目） |
| 代码扫描 | 按语言自动适配（TS/Python/Go/Rust/...） |
| PRD 格式 | 自适应探测（4 组关键词，选命中最多的 2 组） |
| 任务载体 | 自适应识别（plans/phases/tasks/issues） |
| MVP 清单位置 | 自适应搜索（关键词定位） |
| 风险检测 | 基础 14 类 + 配置包专属 + 条件触发 |
| 测试框架 | 自适应识别（jest/vitest/pytest/go test） |
| CI 配置 | 自适应识别（GitHub Actions/GitLab CI/Jenkins） |
| project-context.md | 全 {占位符} 动态填充 |

**任何项目**——电商/教育/SaaS/工具/游戏/IoT/小程序——都能用这个 Skill。

---

## 十、配置包格式

每个配置包（`profiles/*.md`）格式如下：

```markdown
# {项目类型名} Profile

## 项目类型识别条件
- L2 依赖：{依赖关键词}
- L3 PRD：{PRD 关键词}
- L4 代码：{代码模式}

## 专属风险检测项
| 风险 | 检测方式 | 严重度 |
|---|---|---|
| {风险 1} | {检测方式} | {严重度} |
| {风险 2} | {检测方式} | {严重度} |

## 专属 PRD 关键词（追加到自适应探测）
- {关键词 1} / {关键词 2}

## 专属验收项
- {验收项 1}
- {验收项 2}
```

---

## 十一、安装方式

### 11.1 全局安装（一次性）

```bash
# 把整个 project-radar 目录放到全局 skills 目录
cp -r .codex/skills/project-radar ~/.codex/skills/project-radar
```

### 11.2 验证安装

```
$list-skills
```

应看到 `project-radar`。

### 11.3 在新项目里使用

打开任何项目 → 启动主 Agent → 主 Agent 自动调用 project-radar → 5 层识别 → 加载配置包 → 分析 → 提示 → 覆盖检查 → 生成 `project-context.md`。

### 11.4 扩展：新增项目类型

未来如果需要支持新项目类型（如 IoT/游戏/AI），只需：

1. 在 `~/.codex/skills/project-radar/profiles/` 下新建 `{type}.md`
2. 按配置包格式填写识别条件 + 专属风险 + 专属关键词
3. 不改 SKILL.md

---

## 十二、与项目文档的关系

| 文件 | 性质 | 谁生成 | 作用 |
|---|---|---|---|
| `~/.codex/skills/project-radar/SKILL.md` | **通用** | 用户安装 | 引擎，零项目假设 |
| `~/.codex/skills/project-radar/profiles/*.md` | **通用插件** | 用户安装 | 项目类型配置包 |
| `{项目}/.codex/project-context.md` | **项目专属** | Skill 动态生成 | 6 部分全占位符填充 |
| `{项目}/AGENTS.md` | **项目专属** | Skill 建议调整，用户确认 | Agent 宪法 |
| `{项目}/docs/PRD-*.md` | **项目专属** | Skill 建议分层读指引 | 产品需求 |
| `{项目}/{任务载体}/` | **项目专属** | 主 Agent 生成，project-radar 检查覆盖 | 子 Agent 任务清单 |

---

**Skill 结束**

> project-radar 是通用项目雷达，零项目假设，配置驱动规则引擎。引擎 + 插件架构，未来扩展不改代码。
> 每个项目里生成的 `.codex/project-context.md` 是项目专属的 Agent 使用文档，6 部分全 `{占位符}` 动态填充。
> 任何项目——电商/教育/SaaS/工具/游戏/IoT/小程序——都能用这个 Skill。
