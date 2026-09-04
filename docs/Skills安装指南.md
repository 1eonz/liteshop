# LiteShop Skills 安装指南

> 本文件列出 LiteShop 项目相关的 CodeX Skills 市面分析与安装指引。
> **常驻清单的唯一事实源是 AGENTS.md §8.7**（6 个常驻 + 3 个 Demo 临时），本文分析与之一致；如与 AGENTS.md 冲突，以 AGENTS.md 为准。
> 你需要先手动安装这些 skills，主 Agent 才能在 IDE 里自动调用它们优化项目。

---

## 一、Skills 是什么

CodeX Skills 是字节跳动 CodeX IDE 的"技能包"——把一套完整指令、脚本、参考资料打包，AI 加载后能在特定领域发挥专业能力。本质上是给 Agent 装"外挂大脑"，让它不只写代码，还能审代码、跑测试、管提交、写文档。

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

> 下表是市面分析（保留供选型参考）。LiteShop 实际安装范围见 §三（与 AGENTS.md §8.7 一致）。

### 2.1 前端设计类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| **impeccable** | Paul Bakaus | AI 设计词汇层：7 份设计领域参考 + 23 条斜杠命令 + 25 条反模式 + 60 条 CI 检测规则，让 AI 生成的 UI 不再"AI 味" | **常驻**：验收设计审查 / 上线前精细化 / CI 设计检测 | ✅ 常驻 |
| **frontend-design** | Anthropic | 从零生成明确视觉风格的前端界面（排版/配色/动效），避免"AI 模板味" | **Demo 阶段临时**：设计 3 个 Demo 选风格，用完卸载 | ⏸ Demo 临时 |
| **frontend-ui-ux** | code-yeongyu | 微交互/间距/色彩和谐/UI 体验优化 | **Demo 阶段临时**：Demo 细节优化，用完卸载 | ⏸ Demo 临时 |
| **better-interface** | Anthropic | 可访问性 + 交付审查（a11y） | **Demo 阶段临时**：卸载后 a11y 由 impeccable /audit 承接 | ⏸ Demo 临时 |
| frontend-skill | CodeX 官方 | 构建结构清晰且风格克制的前端界面 | 不装（与 frontend-design 重叠） | ❌ |
| design-taste-frontend | Leonxlnx | 避免 AI 模板味，提升设计品味 | 不装（与 frontend-design 重叠） | ❌ |

**Impeccable 与 frontend-design 的关系**：Impeccable 基于 frontend-design 扩展，提供更深层的设计词汇层。两者不冲突——frontend-design 负责"从零设计"（Demo 临时），Impeccable 负责"审查+微调+反模式兜底+CI 检测"（常驻）。

**Impeccable 与项目设计规范的关系**：Impeccable 安装后会在项目根目录生成 `.impeccable.md`，需在里面加一行"优先遵循项目 docs/设计规范.md，不覆盖自定义 CSS 变量。主色 #ff6b6b，禁用 Impeccable 推荐的默认配色"。Impeccable 的反模式库（禁 Inter/Arial/紫色渐变/嵌套卡片/弹跳缓动）和项目的 `docs/设计规范.md`（主色 #ff6b6b、L0-L4 组件分层）互补不冲突。

### 2.2 全栈开发类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| fullstack-developer | Shubhamsaboo | 前端 React + 后端 Node + 数据库 + 认证 + 部署 | 不用（前后端分离架构） | ❌ |
| composition-patterns | CodeX 官方 | 组件组合模式拆分重构、状态管理优化 | 不装（重构场景按需再装） | ❌ |
| cache-components | Vercel | Next.js PPR 和缓存组件最佳实践 | 二期官网时再装 | ⏭ 二期 |

### 2.3 代码审查类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| **code-reviewer** | Google Gemini | 通用代码审查：正确性/可维护性/安全/性能/测试完整性，给出"能合还是得改"结论 | **常驻**：主 Agent 5+1 步验收 + 商业级验收。**审查范围含前端规则**（CSS 冗余、useEffect 依赖、TS 类型、React 性能——原 frontend-code-review 与 react-best-practices 的检查项并入其提示词） | ✅ 常驻 |
| frontend-code-review | Dify (langgenius) | 前端专项：CSS 冗余/useEffect 缺失依赖/命名/TS 类型 | **不单独安装**：检查项并入 code-reviewer 提示词（AGENTS.md §8.7） | ❌ 并入 |
| react-best-practices | Vercel | React/Next.js 项目质量审查与性能分析（8 类 64 条规则） | **不单独安装**：检查项并入 code-reviewer 提示词 | ❌ 并入 |

### 2.4 自动化测试类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| **fix** | Meta (React 团队) | 自动跑 Prettier + Lint，自动修复能修的 | **常驻**：子 Agent 完成后自动修复格式/编译错误 | ✅ 常驻 |
| webapp-testing | Anthropic | 基于 Playwright 自动生成并执行测试脚本 | **不装**：E2E 直接用 Playwright 命令（见 docs/verify-commands.md） | ❌ |

### 2.5 Git/CI 类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| **git-commit** | GitHub | Conventional Commits 规范，自动分析 diff 拆分暂存提交 | **常驻**：子 Agent 小步 commit | ✅ 常驻 |
| pr-creator | Google Gemini | 自动创建符合规范的 PR | **不装**：主 Agent 自己创建 PR | ❌ |

### 2.6 文档与发现类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| update-docs | Vercel | 代码变更自动分析更新对应文档 | **不装**：主 Agent 自己同步文档（契约/错误码） | ❌ |
| find-skills | Vercel Labs | 从技能市场搜索/安装/管理 skills | 可选（发现新 skill 时） | ⏸ 可选 |
| doc-coauthoring | CodeX 官方 | 分阶段协作生成结构清晰文档 | 可选 | ⏸ 可选 |

### 2.7 数据与可视化类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| **chart-visualization** | CodeX 官方 | 根据数据特征选图表类型，生成 ECharts 规范配置 + 对齐设计规范色板 | **常驻（限定加载者）**：仅 plan-12 后台数据看板子 Agent 加载 | ✅ 常驻 |
| data-analysis | CodeX 官方 | SQL 查询 Excel/CSV，多表关联分析 | 可选（后台报表/导出按需） | ⏸ 可选 |

### 2.8 其他实用类

| Skill 名 | 作者 | 核心能力 | LiteShop 用途 | 采用 |
|---|---|---|---|---|
| brainstorming | CodeX 官方 | 开发前强制需求梳理澄清 | 可选（需求设计阶段） | ⏸ 可选 |
| canvas-design | CodeX 官方 | 生成海报/封面等静态视觉内容 | 二期商城模板图 | ⏭ 二期 |
| figma | CodeX 官方 | 解析 Figma 设计稿生成前端代码 | 二期接设计师交付物 | ⏭ 二期 |
| agent-browser | CodeX 官方 | 脚本化浏览器操作 | 不装（E2E 用 Playwright） | ❌ |
| humanizer | Anthropic | 文案自然化，去 AI 腔 | 可选（商品文案/SEO） | ⏸ 可选 |

---

## 三、LiteShop 安装清单（唯一事实源：AGENTS.md §8.7）

### 3.1 常驻 6 个（5 个市场 skill + 1 个全局 project-radar）

```bash
# === 市场安装 5 个 ===
1. code-reviewer        # 代码审查（正确性/安全/性能，含前端规则与 React 性能）
2. fix                  # Prettier + Lint 自动修复格式/编译错误
3. git-commit           # Conventional Commits 规范提交
4. impeccable           # 设计质量：60 条 CI 确定性规则 + /audit /polish /harden
5. chart-visualization  # ECharts 图表配置（仅 plan-12 数据看板子 Agent 加载）

# === 全局安装 1 个 ===
6. project-radar        # 项目雷达（把项目内 .codex/skills/project-radar/SKILL.md
                        #  复制到 ~/.codex/skills/project-radar/SKILL.md，所有项目共用）
```

### 3.2 Demo 阶段临时 3 个（风格确认后卸载）

```bash
7. frontend-design      # 设计 3 个风格 Demo
8. frontend-ui-ux       # Demo 微交互/间距/色彩优化
9. better-interface     # Demo 阶段 a11y 审查（卸载后由 impeccable /audit + axe-core 承接）
```

安装时机：操作手册第一步与常驻 Skills 一并安装；操作手册第二步风格确认后**立即卸载**（操作手册 2.4 的确认指令已含卸载要求）。

### 3.3 明确不装（7 个去向）

| Skill | 去向 | 理由 |
|---|---|---|
| frontend-code-review | 检查项并入 code-reviewer 提示词 | 一个通用审查 skill 已覆盖，单独装浪费上下文 |
| react-best-practices | 检查项并入 code-reviewer 提示词 | 同上 |
| webapp-testing | E2E 直接用 Playwright 命令（docs/verify-commands.md） | 命令已够，不需要 skill 包装 |
| pr-creator | 主 Agent 自己创建 PR | 简单操作不需要外挂 |
| update-docs | 主 Agent 自己同步文档 | 契约/错误码同步是主 Agent 职责 |
| design-taste-frontend | 不装 | 与 frontend-design 重叠 |
| frontend-skill | 不装 | 与 frontend-design 重叠 |

### 3.4 可选装（二期/按需）

```bash
# 二期官网时再装
cache-components        # Next.js PPR 缓存优化
figma                   # Figma 设计稿转代码

# 按需
brainstorming           # 需求澄清对话
data-analysis           # 后台报表/导出
humanizer               # 商品文案/SEO 文案
```

---

## 四、安装步骤（你手动操作）

### 4.1 通过 CodeX 技能市场安装（推荐）

1. 打开 CodeX IDE
2. 侧边栏点击"技能"图标（或 设置 → 规则和技能 → 技能）
3. 搜索下列 skill 名，逐个点击"安装"：

   **常驻（5 个）**：
   - `code-reviewer`
   - `fix`
   - `git-commit`
   - `impeccable`
   - `chart-visualization`

   **Demo 阶段临时（3 个，风格确认后卸载）**：
   - `frontend-design`
   - `frontend-ui-ux`
   - `better-interface`

4. 全局安装 project-radar：把项目内 `.codex/skills/project-radar/SKILL.md` 复制到 `~/.codex/skills/project-radar/SKILL.md`
5. 安装后验证：在对话窗输入 `$list-skills`，应看到上述 8 个市场 skill + 全局 project-radar

### 4.2 通过对话让 CodeX 创建（备选）

如果某个 skill 在市场找不到，可直接对话：

```
帮我创建一个名为 code-reviewer 的 SKILL.md，参考 Google Gemini 版本，
功能是代码审查：正确性/可维护性/安全/性能/测试完整性，含前端规则
（CSS 冗余/useEffect 依赖/TS 类型/React 性能），给出"能合还是得改"结论。
```

CodeX 会自动生成 `.codex/skills/code-reviewer/SKILL.md`。

### 4.3 Demo 临时 Skills 的卸载

操作手册第二步风格确认后（操作手册 2.4 指令已含），卸载 3 个临时 skill：
1. 设置 → 规则和技能 → 技能 → 找到 frontend-design / frontend-ui-ux / better-interface → 卸载
2. `$list-skills` 验证只剩 5 个市场常驻 + project-radar

---

## 五、Skills 使用时机（与主 Agent 流程对齐）

### 5.1 设计 Demo 阶段（临时 Skills 在岗期）

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| frontend-design（临时） | 设计 3 个风格 Demo 时 | 子 Agent prompt 里要求"加载 frontend-design skill" |
| frontend-ui-ux（临时） | Demo 细节优化 | 子 Agent prompt 里要求"加载 frontend-ui-ux 优化微交互" |
| better-interface（临时） | Demo a11y 检查 | 子 Agent prompt 里要求"加载 better-interface 审查可访问性" |
| impeccable（常驻） | Demo 设计审查 + 精细化 | 子 Agent 完成后调用 `/audit` 设计审查 + `/polish` 精细化 |

### 5.2 编码阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| project-radar（全局） | 每 plan 启动前 / 完成后 / 每批结束 / 验收前 | 更新 project-context.md、重复检测、需求覆盖检查（AGENTS.md §8.5） |
| fix（常驻） | 每个子 Agent 完成后 | 5+1 步验收前先跑 fix 修格式 |

### 5.3 数据可视化阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| chart-visualization（常驻） | plan-12 后台数据看板子 Agent | 子 Agent prompt 里要求"加载 chart-visualization skill，基于看板数据生成 ECharts 配置，色板对齐 docs/设计规范.md 的 --color-* 变量，禁硬编码颜色" |

### 5.4 验收阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| code-reviewer（常驻） | 主 Agent 5+1 步验收 + 商业级验收 | "用 code-reviewer 审查 backend/ 目录"（前端规则同 skill 覆盖） |
| impeccable（常驻） | 设计质量审查 + 上线前 | "调用 /audit 做全面设计审查（排版/色彩/间距/对比度/a11y），/polish 上线前精细化，/harden 生产就绪检查" |

### 5.5 提交阶段

| Skill | 触发时机 | 主 Agent 调用方式 |
|---|---|---|
| git-commit（常驻） | 子 Agent 小步提交 | "用 git-commit 规范提交" |

（PR 创建与文档同步由主 Agent 自己完成，不用 skill；E2E 用 Playwright 命令。）

---

## 六、Skills 组合策略（效果倍增）

### 6.1 验收全流程组合

```
project-radar（重复检测） + code-reviewer（代码审查） + fix（格式修复） + git-commit（规范提交）
  ↓
  1. project-radar 对照 project-context.md 查重复
  2. code-reviewer 审查代码（含前端规则）
  3. fix 修复格式问题
  4. git-commit 规范提交
```

### 6.2 前端交付组合

```
code-reviewer + impeccable + Playwright
  ↓
  1. code-reviewer 审查代码质量（CSS 冗余/useEffect 依赖/TS 类型/React 性能均覆盖）
  2. impeccable /audit 审查设计质量（排版/色彩/间距/对比度/a11y）
  3. cd tests/e2e && pnpm playwright test 跑 E2E
```

### 6.3 后端交付组合

```
code-reviewer + project-radar
  ↓
  1. code-reviewer 审查后端代码（SQL 注入/XSS/性能）
  2. project-radar 重复检测
  3. 契约/错误码文档同步由主 Agent 自己做
```

---

## 七、避坑指南（血泪经验）

### 7.1 不要贪多

- **常驻上限 6 个 + Demo 临时 3 个（用完即卸）**——装 10+ skill 会导致上下文臃肿，响应速度下降
- LiteShop 常驻 6 个（5 市场 + project-radar）已覆盖全部验收/审查/提交环节，不追求大而全
- 被砍掉的 7 个去向见 §3.3：检查项并入 code-reviewer、命令替代 skill、主 Agent 自己做

### 7.2 Skill 顺序很重要

- 执行顺序靠后的 skill 会覆盖前面的规则
- **把 frontend-design 放最后**，否则好看的设计会被后面的通用规则覆盖
- 配置 `.codex/skills/order.txt` 控制执行顺序（如有）

### 7.3 避免规则重叠

- `frontend-design` + `design-taste-frontend`：功能重叠，只装前者（Demo 临时）
- `code-reviewer` + `frontend-code-review`：**已合并**——后者检查项并入 code-reviewer 提示词，不单独装
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

- 关键业务逻辑（支付/库存/订单状态机）**仍需人工 review**——AGENTS.md §8.3 试点校准把 plan-05/06 事务代码定为人工逐行 review 卡点
- Skill 只是辅助，不能完全替代人工审查
- PRD 第十二章"人工介入红线"列出的场景必须人工确认

---

## 八、自定义 Skills（LiteShop 专属）

主 Agent 在操作手册第一步自动创建 **4 个项目自定义 skill**：

```
.codex/skills/
├── project-radar/SKILL.md        # 通用引擎的项目内副本（安装源，复制到全局后由全局副本生效）
├── liteshop-contract/SKILL.md    # 契约审查：检查代码是否符合 OpenAPI/shared-types
├── liteshop-territory/SKILL.md   # 领地检查：子 Agent 改动是否越界
├── liteshop-verify/SKILL.md      # 5+1 步验收：自动跑验证命令+查幻觉+抽查+重复检测
└── liteshop-style/SKILL.md       # 设计规范：检查是否用 CSS 变量、是否硬编码
```

**口径：4 个项目自定义 + 1 个全局 project-radar**（project-radar 是通用 Skill，仅一个 SKILL.md 文件，装在用户目录全局生效，所有项目共用；项目内的 `.codex/skills/project-radar/` 只是安装源备份）。

安装方式：把项目内 `.codex/skills/project-radar/SKILL.md`（仅一个文件）复制到 `~/.codex/skills/project-radar/SKILL.md` 即可全局生效。

**project-radar 解决以下问题**：
- **上下文爆炸**：5 层识别项目类型，自适应 PRD 格式探测，生成分层读指引，主 Agent 不再一次读全 PRD
- **重复造轮子**：在项目内生成 `.codex/project-context.md`（代码索引），子 Agent 启动前知道项目已有什么，5+1 步验收时重复检测
- **子 Agent 盲目编码**：主 Agent 把 project-context 摘要塞进 Task query，子 Agent 不再盲目
- **风险预警**：基础 14 类 + 配置包专属风险（动态生成）+ 条件触发，用 AskUserQuestion 提示用户是否调整
- **需求遗漏**：自适应关键词提取 PRD 需求点（§7.1 只取 [1a] 项），自适应任务载体对照，遗漏则 AskUserQuestion 提示补拆
- **验收遗漏**：自适应定位 MVP 清单，对照验收清单检查覆盖
- **文档调整建议**：只建议不擅改，用户逐项确认后才修改

完整机制定义见 **AGENTS.md §8.5**。

---

## 九、安装完成验证清单

- [ ] CodeX IDE 已安装并登录
- [ ] 5 个常驻市场 skill 已安装（`$list-skills` 能看到：code-reviewer / fix / git-commit / impeccable / chart-visualization）
- [ ] project-radar 已复制到全局 `~/.codex/skills/project-radar/SKILL.md`
- [ ] 3 个 Demo 临时 skill 已安装（frontend-design / frontend-ui-ux / better-interface，风格确认后卸载）
- [ ] 项目根目录有 `.codex/skills/` 目录（主 Agent 第一步创建）
- [ ] 4 个 LiteShop 专属 skill 已自动生成（liteshop-contract / liteshop-territory / liteshop-verify / liteshop-style）
- [ ] 每个 skill 的 SKILL.md 末尾已加"优先遵循项目设计系统"那一行
- [ ] `codex skills update` 已执行一次

---

## 十、Skills 与 PRD/AGENTS.md 的关系

| Skill | 状态 | PRD/AGENTS.md 对应 |
|---|---|---|
| project-radar | 常驻（全局） | AGENTS.md §8.5（防重复/需求覆盖/MVP 清单提取 [1a]） |
| code-reviewer | 常驻 | AGENTS.md §5 验证要求、PRD E15 验收清单、AGENTS.md §4.3 前端代码约束（frontend-code-review / react-best-practices 检查项已并入） |
| fix | 常驻 | PRD E1.5 验证命令 |
| git-commit | 常驻 | AGENTS.md §4.5 提交与分支 |
| impeccable | 常驻 | docs/设计规范.md（反模式兜底 + 设计审查 + CI 检测）+ PRD E5.4 a11y（/audit 承接） |
| chart-visualization | 常驻（仅 plan-12 加载） | PRD E1.3 前端性能约束（图表按需懒加载）+ docs/设计规范.md 色板对齐 |
| frontend-design | Demo 临时 | docs/设计规范.md |
| frontend-ui-ux | Demo 临时 | docs/设计规范.md |
| better-interface | Demo 临时 | PRD E5.4 a11y 合规 |

---

**文件结束**

> Skills 是 LiteShop 项目质量兜底的关键。常驻 6 个覆盖验收/审查/提交全环节，Demo 临时 3 个用完即卸，不给子 Agent 上下文添负担。清单唯一事实源：AGENTS.md §8.7。
> 配套：`操作手册.md`（你本人看的 4 条指令操作指南）
