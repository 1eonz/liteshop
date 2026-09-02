# LiteShop Skills 安装指南

> 本文件列出 LiteShop 项目推荐的所有 CodeX Skills，含**市面可用 skills 分析、安装命令、使用时机、组合策略**。
> 你需要先手动安装这些 skills，主 Agent 才能在 IDE 里自动调用它们优化项目。

---

## 一、Skills 是什么

CodeX Skills 是字节跳动 CodeX IDE 的"技能包"——把一套完整指令、脚本、参考资料打包，AI 加载后能在特定领域发挥专业能力。本质上是给 Agent 装"外挂大脑"，让它不只写代码，还能审代码、跑测试、管 PR、写文档。

**关键特性**：
- Skill 是 `.md` 文件（`SKILL.md`），装在 `.codex/skills/{skill-name}/` 目录
- Agent 在对话中遇到匹配场景时自动触发，也可手动 `$调用 skill-name`
- 项目级 skill 放 `.codex/skills/`，全局级放用户目录

**安装方式**：
1. CodeX IDE → 设置 → 规则和技能 → 技能 → 创建并导入 SKILL.md
2. 或对话让 CodeX 帮你创建："帮我创建一个代码审查的 SKILL，重点关注安全和性能"
3. 或从技能市场搜索安装（推荐路径，已通过官方审核）

---

## 二、市面可用 Skills 完整清单（按场景分类）

### 2.1 前端设计类（5 个，LiteShop 必装）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **frontend-design** | Anthropic | 从零生成明确视觉风格的前端界面（排版/配色/动效），避免"AI 模板味" | 设计 3 个 Demo 让你选风格 | ⭐⭐⭐⭐⭐ |
| **frontend-skill** | CodeX 官方 | 构建结构清晰且风格克制的前端界面，规范信息层级与排版 | 商城/后台页面布局 | ⭐⭐⭐⭐ |
| **frontend-ui-ux** | code-yeongyu | 微交互/间距/色彩和谐/UI 体验优化 | 商品卡片、SKU 抽屉细节优化 | ⭐⭐⭐⭐ |
| **design-taste-frontend** | Leonxlnx | 避免 AI 模板味，提升设计品味 | 全站视觉品味兜底 | ⭐⭐⭐ |
| **better-interface** | Anthropic | 可访问性 + 交付审查（a11y） | PRD E5.4 a11y 合规 | ⭐⭐⭐⭐ |

**LiteShop 装哪些**：`frontend-design` + `frontend-ui-ux` + `better-interface` 三个必装，其他可选。

### 2.2 全栈开发类（3 个）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **fullstack-developer** | Shubhamsaboo | 前端 React + 后端 Node + 数据库 + 认证 + 部署 | 不直接用（我们前后端分离） | ⭐⭐ |
| **composition-patterns** | CodeX 官方 | 组件组合模式拆分重构、状态管理优化 | 共享组件库重构 | ⭐⭐⭐⭐ |
| **cache-components** | Vercel | Next.js PPR 和缓存组件最佳实践 | 官网 ISR 缓存优化（二期） | ⭐⭐⭐⭐（二期必装） |

### 2.3 代码审查类（3 个，LiteShop 必装）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **code-reviewer** | Google Gemini | 通用代码审查：正确性/可维护性/安全/性能/测试完整性，给出"能合还是得改"结论 | 主 Agent 5 步验收时调用 | ⭐⭐⭐⭐⭐ |
| **frontend-code-review** | Dify (langgenius) | 前端专项：CSS 冗余/useEffect 缺失依赖/命名/TS 类型 | 前端子 Agent 完成后调用 | ⭐⭐⭐⭐⭐ |
| **react-best-practices** | Vercel | React/Next.js 项目质量审查与性能分析（8 类 64 条规则） | 全前端包审查 | ⭐⭐⭐⭐ |

**LiteShop 装哪些**：3 个全装。`code-reviewer` 用于主 Agent 验收，`frontend-code-review` 用于前端代码审查，`react-best-practices` 用于性能优化。

### 2.4 自动化测试类（2 个，LiteShop 必装）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **webapp-testing** | Anthropic | 基于 Playwright 自动生成并执行测试脚本，截图/控制台日志/DOM 检查 | 集成验证子 Agent 用 | ⭐⭐⭐⭐⭐ |
| **fix** | Meta (React 团队) | 自动跑 Prettier + Lint，自动修复能修的 | 子 Agent 完成后自动修复格式 | ⭐⭐⭐⭐⭐ |

### 2.5 Git/CI 类（2 个，LiteShop 必装）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **git-commit** | GitHub | Conventional Commits 规范，自动分析 diff 拆分暂存提交 | 子 Agent 小步 commit | ⭐⭐⭐⭐⭐ |
| **pr-creator** | Google Gemini | 自动创建符合规范的 PR，含分支检查/模板/预检脚本 | 合并 main 前的 PR | ⭐⭐⭐⭐ |

### 2.6 文档与发现类（3 个）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **update-docs** | Vercel | 代码变更自动分析更新对应文档 | OpenAPI/AGENTS.md 同步 | ⭐⭐⭐⭐ |
| **find-skills** | Vercel Labs | 从技能市场搜索/安装/管理 skills | 发现新 skill | ⭐⭐⭐ |
| **doc-coauthoring** | CodeX 官方 | 分阶段协作生成结构清晰文档 | PRD/设计文档协作 | ⭐⭐⭐ |

### 2.7 数据与可视化类（2 个）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **chart-visualization** | CodeX 官方 | 根据数据特征选图表类型，生成可视化 | 后台数据看板 ECharts | ⭐⭐⭐⭐ |
| **data-analysis** | CodeX 官方 | SQL 查询 Excel/CSV，多表关联分析 | 后台报表/导出 | ⭐⭐⭐ |

### 2.8 其他实用类（3 个）

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 推荐度 |
|---|---|---|---|---|
| **brainstorming** | CodeX 官方 | 开发前强制需求梳理澄清，交互式对话形成方案 | 阶段 0 契约设计 | ⭐⭐⭐⭐ |
| **canvas-design** | CodeX 官方 | 生成海报/封面等静态视觉内容 | 二期商城模板图 | ⭐⭐⭐ |
| **figma** | CodeX 官方 | 解析 Figma 设计稿生成前端代码 | 二期接设计师交付物 | ⭐⭐⭐ |
| **agent-browser** | CodeX 官方 | 脚本化浏览器操作，数据提取/自动化流程 | E2E 测试辅助 | ⭐⭐⭐ |
| **humanizer** | Anthropic | 文案自然化，去 AI 腔 | 商品文案/SEO 文案 | ⭐⭐⭐ |

---

## 三、LiteShop 推荐安装清单（11 个核心 + 4 个可选）

### 3.1 核心必装（11 个，1a 期全流程覆盖）

按场景顺序：

```bash
# === 前端设计（设计 Demo 阶段） ===
1. frontend-design          # 设计 3 个风格 Demo
2. frontend-ui-ux           # 微交互/间距/色彩优化
3. better-interface         # a11y 可访问性审查

# === 代码审查（子 Agent 完成后） ===
4. code-reviewer            # 通用审查（后端+前端）
5. frontend-code-review     # 前端专项审查
6. react-best-practices     # React/Next.js 性能优化

# === 自动化测试 ===
7. webapp-testing           # Playwright E2E 测试生成
8. fix                      # Prettier + Lint 自动修复

# === Git/CI ===
9. git-commit               # Conventional Commits 规范提交
10. pr-creator              # PR 自动创建

# === 文档同步 ===
11. update-docs             # 代码变更同步文档
```

### 3.2 可选装（4 个，按需）

```bash
# 二期官网时再装
12. cache-components        # Next.js PPR 缓存优化
13. figma                   # Figma 设计稿转代码

# 数据看板开发时装
14. chart-visualization     # ECharts 图表生成

# 需求设计阶段装
15. brainstorming           # 需求澄清对话
```

### 3.3 不推荐安装

- `fullstack-developer`：前后端不分离的快速 MVP 场景才用，LiteShop 是分离架构
- `design-taste-frontend`：与 `frontend-design` 重叠，避免规则互相覆盖
- `frontend-skill`：与 `frontend-design` 重叠

---

## 四、安装步骤（你手动操作）

### 4.1 通过 CodeX 技能市场安装（推荐）

1. 打开 CodeX IDE
2. 侧边栏点击"技能"图标（或 设置 → 规则和技能 → 技能）
3. 搜索下列 skill 名，逐个点击"安装"：
   - `frontend-design`
   - `frontend-ui-ux`
   - `better-interface`
   - `code-reviewer`
   - `frontend-code-review`
   - `react-best-practices`
   - `webapp-testing`
   - `fix`
   - `git-commit`
   - `pr-creator`
   - `update-docs`

4. 安装后验证：在对话窗输入 `$list-skills`，应看到上述 11 个

### 4.2 通过对话让 CodeX 创建（备选）

如果某个 skill 在市场找不到，可直接对话：

```
帮我创建一个名为 frontend-design 的 SKILL.md，参考 Anthropic 官方版本，
功能是从零生成明确视觉风格的前端界面，注重排版/配色/动效。
```

CodeX 会自动生成 `.codex/skills/frontend-design/SKILL.md`。

### 4.3 手动导入 SKILL.md（高级）

1. 从 GitHub 下载对应 SKILL.md 文件
2. 在项目根目录创建 `.codex/skills/{skill-name}/SKILL.md`
3. 把下载的文件内容粘进去
4. 重启 CodeX IDE 或刷新技能列表

---

## 五、Skills 使用时机（与主 Agent 流程对齐）

### 5.1 设计 Demo 阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| frontend-design | 设计 3 个风格 Demo 时 | 子 Agent prompt 里要求"加载 frontend-design skill" |
| frontend-ui-ux | Demo 细节优化 | 子 Agent prompt 里要求"加载 frontend-ui-ux 优化微交互" |
| brainstorming | 阶段 0 契约设计 | 主 Agent 自己调用，澄清需求 |

### 5.2 编码阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| composition-patterns | 共享组件重构 | 子 Agent 完成后用此 skill 审查组件结构 |
| fix | 每个子 Agent 完成后自动触发 | 主 Agent 5 步验收前先跑 fix 修格式 |

### 5.3 验收阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| code-reviewer | 主 Agent 5 步验收 | "用 code-reviewer 审查 backend/ 目录" |
| frontend-code-review | 前端子 Agent 完成后 | "用 frontend-code-review 审查 packages/h5-app/" |
| react-best-practices | 性能优化阶段 | "用 react-best-practices 审查 packages/h5-app/ 性能" |
| better-interface | a11y 检查 | "用 better-interface 审查可访问性" |

### 5.4 测试阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| webapp-testing | 集成验证子 Agent | "用 webapp-testing 生成 Playwright E2E 测试" |

### 5.5 提交阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| git-commit | 子 Agent 小步提交 | "用 git-commit 规范提交" |
| pr-creator | 合并 main 前 | "用 pr-creator 创建 PR" |
| update-docs | 代码变更后 | "用 update-docs 同步 docs/api-contracts/" |

---

## 六、Skills 组合策略（效果倍增）

### 6.1 PR 全流程组合

```
pr-creator + code-reviewer + fix
  ↓
  1. pr-creator 跑预检（lint/test）
  2. code-reviewer 审查代码
  3. fix 修复格式问题
  4. pr-creator 创建 PR
```

### 6.2 前端交付组合

```
frontend-code-review + webapp-testing + better-interface
  ↓
  1. frontend-code-review 审查代码质量
  2. better-interface 审查 a11y
  3. webapp-testing 生成 E2E 测试
```

### 6.3 后端交付组合

```
code-reviewer + update-docs
  ↓
  1. code-reviewer 审查后端代码（SQL 注入/XSS/性能）
  2. update-docs 同步 OpenAPI 契约文档
```

---

## 七、避坑指南（血泪经验）

### 7.1 不要贪多

- **最多装 5 个全局 skill + 项目级按需**
- 装 10+ skill 会导致上下文臃肿，响应速度下降
- LiteShop 推荐 11 个核心，已是上限

### 7.2 Skill 顺序很重要

- 执行顺序靠后的 skill 会覆盖前面的规则
- **把 frontend-design 放最后**，否则好看的设计会被后面的通用规则覆盖
- 配置 `.codex/skills/order.txt` 控制执行顺序（如有）

### 7.3 避免规则重叠

- `frontend-design` + `design-taste-frontend`：功能重叠，二选一
- `code-reviewer` + `frontend-code-review`：不重叠（一个通用一个前端专项），可同时用
- `frontend-skill` + `frontend-design`：重叠，选 `frontend-design`

### 7.4 与项目设计系统的关系

- Skill 推荐的字体/配色/间距**不能覆盖**项目的 `docs/设计规范.md`
- 在每个 skill 的 SKILL.md 末尾加一行：

  ```
  优先遵循项目已有设计系统（docs/设计规范.md），不覆盖自定义 CSS 变量。
  ```

- LiteShop 的 `#ff6b6b` 主色、8 倍数间距、L0-L4 组件分层等规约**优先于任何 skill 推荐**

### 7.5 及时更新

```bash
# 定期执行（每月一次）
codex skills update
```

获取最新规则，避免用过时的最佳实践。

### 7.6 人工兜底

- 关键业务逻辑（支付/库存/订单状态机）**仍需人工 review**
- Skill 只是辅助，不能完全替代人工审查
- PRD 第十二章"人工介入红线"列出的场景必须人工确认

---

## 八、自定义 Skills（LiteShop 专属）

主 Agent 在阶段 0 会自动创建 4 个项目专属 skill：

```
.codex/skills/
├── liteshop-contract/SKILL.md    # 契约审查：检查代码是否符合 OpenAPI/shared-types
├── liteshop-territory/SKILL.md   # 领地检查：子 Agent 改动是否越界
├── liteshop-verify/SKILL.md      # 5+1 步验收：自动跑验证命令+查幻觉+抽查+重复检测
└── liteshop-style/SKILL.md       # 设计规范：检查是否用 CSS 变量、是否硬编码
```

此外还有一个**通用全局 Skill**（仅一个文件，装在用户目录）：

```
~/.codex/skills/
└── project-radar/SKILL.md       # 项目雷达：通用引擎，5 层识别项目类型+动态生成配置包+分析风险+提示用户调整+需求覆盖检查+生成 project-context.md
```

**project-radar 是通用 Skill**，仅一个 SKILL.md 文件，装一次，所有项目共用。配置包不预创建，主 Agent 在每个项目里根据实际情况动态生成。它解决以下问题：
- **上下文爆炸**：5 层识别项目类型，自适应 PRD 格式探测，生成分层读指引，主 Agent 不再一次读全 PRD
- **重复造轮子**：在项目内生成 `.codex/project-context.md`（代码索引），子 Agent 启动前知道项目已有什么，5+1 步验收时重复检测
- **子 Agent 盲目编码**：主 Agent 把 project-context 摘要塞进 Task query，子 Agent 不再盲目
- **风险预警**：基础 14 类 + 配置包专属风险（动态生成）+ 条件触发，用 AskUserQuestion 提示用户是否调整
- **需求遗漏**：自适应关键词提取 PRD 需求点，自适应任务载体对照，遗漏则 AskUserQuestion 提示补拆
- **验收遗漏**：自适应定位 MVP 清单，对照验收清单检查覆盖
- **文档调整建议**：只建议不擅改，用户逐项确认后才修改

安装方式：把 `.codex/skills/project-radar/SKILL.md`（仅一个文件）复制到 `~/.codex/skills/project-radar/SKILL.md` 即可全局生效。

---

## 九、安装完成验证清单

- [ ] CodeX IDE 已安装并登录
- [ ] 11 个核心 skill 已安装（`$list-skills` 能看到）
- [ ] 项目根目录有 `.codex/skills/` 目录（主 Agent 阶段 0 创建）
- [ ] 4 个 LiteShop 专属 skill 已自动生成
- [ ] 每个 skill 的 SKILL.md 末尾已加"优先遵循项目设计系统"那一行
- [ ] `codex skills update` 已执行一次

---

## 十、Skills 与 PRD/AGENTS.md 的关系

| Skill | PRD/AGENTS.md 对应 |
|---|---|
| frontend-design | docs/设计规范.md |
| code-reviewer | AGENTS.md §5 验证要求、PRD E15 验收清单 |
| frontend-code-review | AGENTS.md §4.3 前端代码约束 |
| react-best-practices | PRD E1.3 前端性能约束 |
| webapp-testing | PRD E15.1 验收清单 |
| fix | PRD E1.5 验证命令 |
| git-commit | AGENTS.md §4.5 提交与分支 |
| pr-creator | AGENTS.md §8.4 人工介入红线（合并决策） |
| update-docs | PRD D2.4 枚举同步、E7.1 OpenAPI |
| better-interface | PRD E5.4 a11y 合规 |
| brainstorming | PRD D8.1 阶段 0 契约先行 |

---

**文件结束**

> Skills 是 LiteShop 项目质量兜底的关键。装好 skills 后，主 Agent 在每个阶段自动调用对应 skill 优化代码/审查/测试/提交，最终交付可商用的项目。
> 配套：`操作手册.md`（你本人看的逐步操作指南）
