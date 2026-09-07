# CRM 项目前端实践借鉴分析

> 生成日期：2026-09-07
> 分析对象：`D:\work\123\l`（励销云 CRM，多人长周期迭代项目）
> 子项目构成：crm-pc-frontend（主前端，umi 3 + React 16 + antd 4 + MobX + 纯 JS）、crm-frontend-admin（admin 子应用，qiankun 微前端）、lxComponent（father 构建 + dumi 文档站的组件库）、crm-common-component（设计 token 与环境配置库）
> 分析方式：2 个并行子任务精读约 60 个关键文件 + grep 全库验证，所有结论附 `文件:行号` 证据（路径相对 `D:\work\123\l`）
> 本文档与《代码分析报告与修复建议.md》互补：该报告的 C/H/M/L 编号在下文交叉引用

> 复核说明：本文只借鉴 CRM 的工程模式，不照搬其 umi/React 16/antd/MobX 技术栈。涉及新包、公共包和权限缓存的建议均为候选方案，必须在出现真实调用方并完成依赖与安全评估后落地。

---

## 一、项目概况

CRM 是典型的企业级多人维护项目：43 个按域拆分的 service 文件（约 9155 行）、23 个 MobX store、19 个环境配置文件（环境 × 灰度 × 产品线三维矩阵）、13 个带文档的组件库组件。技术栈与 LiteShop 差异大（umi 3 / React 16 / JS / less / MobX），因此借鉴的是**工程模式与数据流设计**，而非代码本身。

**一句话画像**：精华集中在权限系统数据流、服务层三件套（URL 字典/竞态取消/错误码缺省页）、组件库文档与 token 体系；坑集中在 window 灰度变量、巨型文件、新旧并存不清理——坑的部分恰好从反面印证了 LiteShop 现有规约（AGENTS.md）的价值。

---

## 二、第一梯队：直接填补 LiteShop 现有缺口（4 项）

### 2.1 权限快照数据流（对应 plan-10 RBAC / M7 权限仅展示层）

CRM 最值钱的子系统，四层设计：

| 层 | CRM 实现 | 证据 |
|---|---|---|
| 聚合拉取 | `Promise.all` 并行请求 5 个接口（模块开关/权限列表/字段权限/组织配置/阶段推进器），一次组装权限快照 | permissionService.js:56-99 |
| 扁平化 | `permissions.forEach(role => result[`${role.subject}_${role.action}`] = true)`，压成 `customer_show`、`lead_edit` 这样的 O(1) 查找 map | permissionService.js:68-70 |
| 缓存校验 | localStorage 带 15 分钟过期；读缓存四条件：非空、未过期、有 userToken、**userToken 与当前登录一致** | permissionService.js:95, 122-127 |
| 错峰刷新 | 8-10 分钟随机间隔定时刷新（注释明言"目的是为了错峰"，避免全员同时打权限接口）；登出自清；3 分钟内更新过则跳过本轮 | permissionService.js:143-161 |

**LiteShop 落地方式**（React Query + Zustand 平移）：

```ts
// 权限扁平化（services 层）
function flattenPermissions(permissions: Permission[]): Record<string, boolean> {
  return Object.fromEntries(
    permissions.map((p) => [`${p.subject}_${p.action}`, true] as const),
  );
}

// Zustand accessStore：快照 + token 一致性校验（防切号读到上一个人权限）
// React Query：staleTime 15min 天然替代手写过期；refetchInterval + 随机抖动实现错峰
// 消费：useAccess('order_ship') 式 O(1) 判断，按钮显隐直接读扁平 map
```

**userToken 一致性校验**这个细节是电商项目极易踩的坑（切号/多标签页场景），必须保留。

### 2.2 错误码 → 缺省页映射（对应 M3 错误处理未建模 ApiError）

CRM 的设计：错误码不是弹 toast 了事，而是映射到**带解释文案的路由缺省页**：

```js
// src/constant/error-code.js
export default {
  401: 'notAccessed',        // 数据权限不够
  100112: 'customerCommon',  // 被转移到客户公海
  100100: 'noPerOrNoData',   // 数据已删除
  networkError: 'networkError',
};

// 领域 service 的 catch 里（customer.js:140-158）
history.push({ pathname: '/nodataperm/' + _.get(errorCodeObj, `${code}`, 'networkError') });
```

**LiteShop 落地方式**：结合现有三层错误结构（code/i18nKey/details）：

- 404（商品下架/删除）、403（无权限）、订单不存在类错误码 → 路由跳转 H5 兜底页（复用现有 EmptyState 组件 + 解释文案）
- 其余业务错误 → toast（对应宪法"组件层 toast"）
- 映射表与 `docs/error-codes.md` 联动，避免两处维护

### 2.3 集中式 URL 字典 + REST 路径模板（配合 H3 幂等键改造一起做）

CRM：538 行、约 500 个 key 的 URL 常量表（apiUrl.js:6-538），每个 key 带中文用途注释；`{id}` 占位符由拦截器统一替换（axios-transform-url.js:4-39）。

**LiteShop 落地方式**：各 service 文件里 URL 字符串目前散落硬编码。endpoint 属于 API/service 层，不放进领域类型包；若确有跨端复用，建议新增轻量 `packages/shared-api-contracts/`，否则先按应用维护 `src/service/endpoints.ts`。示意：

```ts
export const endpoints = {
  orders: '/api/v1/orders',
  orderDetail: '/api/v1/orders/{id}',
  orderItems: '/api/v1/order-items/{id}',
  // ...
} as const;

// api 封装层做模板替换
export function fillPath(template: string, params: Record<string, string | number>): string {
  return Object.entries(params).reduce(
    (url, [key, value]) => url.replace(`{${key}}`, String(value)),
    template,
  );
}
```

改后端路径只动一处；与 H3（幂等键绑定逻辑动作）改造可放同一批 PR。后续若 endpoint 数量和参数类型稳定，再升级为按 endpoint 推导参数的强类型 helper，避免把任意 key 都接受为字符串。

### 2.4 带 TTL + 数组命名空间的 storage 封装

CRM（storage.js:11-49）：数组 key 拼复合键天然带命名空间；写时包一层 `{ data, writeTime, expires }`，读时自动判过期并惰性清理；同基类派生 Local/Session 双实现。

**LiteShop 落地方式**：可在 app 的 utils 下先做最小 TTL 封装；只有出现至少两个真实调用方时再提升到 shared 包。权限、购物车和草稿缓存必须绑定用户/租户/token 指纹，登出、切号和 token 失效时主动清理，不能直接照搬 CRM 的 localStorage 方案。

```ts
storage.setItem(['user', userId, 'cart-draft'], draft, 30 * 60_000); // 30 分钟 TTL
storage.setItem(['table-page-size', 'admin-orders', userId], 20);    // 分页记忆
```

购物车草稿、筛选记忆、分页 per_page 记忆直接复用。

---

## 三、第二梯队：配合已有决策一起做（4 项）

### 3.1 设计 token 双源合一（对应 M7 tokens 混乱 + H6 UI 库决策）

CRM 的 crm-common-component/config/colors.js：`merge(业务 Tailwind 色板, require('lxui/config/colors'))` 让组件库 antd 主题色与业务色板**同源**——改一处，antd 组件与业务样式同时生效。色板按 Tailwind 惯例组织 50-900 十档；primary 走 CSS 变量 + `withOpacity` 支持透明度修饰符。

**LiteShop 落地方式**：当前方向是不引入 antd5/antd-mobile，`shared-tokens` 作为唯一 token 源，未来 ui-kit 只做桥接消费：

```
tokens.css（唯一源头，修复 M7 后）
  ├─ CSS 变量 --color-*          → Tailwind v4 / 业务样式消费
  └─ ui-kit 的 --ui-* 桥接变量   → admin / h5 共享组件消费
```

这正是 AGENTS.md"禁硬编码颜色"的工程化保障：改 `--color-primary` 一处，三端全生效。

> **2026-09-07 复核**：ui-kit 仍是待实施方案，不应在未确认依赖与宪法条款前创建包。`shared-tokens → --ui-*` 的桥接只能有一个事实源，不能在 ui-kit 内复制一套默认业务 token。

### 3.2 组件文档共址 + prop 级版本标注（对应 shared-components 零文档零测试）

CRM 的 lxComponent：每个组件目录固定三件套 `index.tsx + index.less + index.md`；文档含可运行 demo + 五列 API 表（参数/说明/类型/默认值/**版本**），版本列精确到 prop 级（如 `autoScroll` 标注 `1.0.16` 引入）；集中式 updateLog 用 `[A]/[U]/[F]`（Added/Updated/Fixed）+ issue 编号格式。

**LiteShop 落地方式**：

- shared-components 每组件目录放 `Xxx.stories.tsx`（Storybook，宪法 E2.4 本就要求），文档与组件同 PR 演进，杜绝漂移
- CHANGELOG 条目（§4.4.6 已要求）补"prop 引入版本"维度
- updateLog 的 `[A]/[U]/[F]` + issue 号格式直接采用

### 3.3 受控/非受控双模式组件协议（shared-components 通用件规范）

CRM 自研分页器（pagination/index.jsx:66-100）：`current` 未传走内部 state（非受控），传了跟随 props（受控）；props 协议有完整 JSDoc（作者/日期/defaultCurrent/current/pageSizeOptions/showTotal）。

**LiteShop 落地方式**：Pagination/EmptyState/Skeleton 等通用件照此规范，但用 TS `interface XxxProps`（比 JSDoc 强）。受控/非受控兼容是多人维护下通用组件的正确打开方式，避免"想受控就得改组件源码"。

### 3.4 版本化发布目录（对齐部署发布规范的 tag 回滚）

CRM：OSS 静态资源按 `releases/${VERSION}/` 不可变目录发版，`current` 是软链指向当前版本——**回滚 = 把 current 指回旧目录，秒级完成**（version.js:1-4）。

**LiteShop 落地方式**：1a 期只取"版本目录 + current 指针"这一半（配合现有 tag 回滚脚本）；灰度双轨（独立 CDN 域名 + `x-lx-gid` 请求头）留增长期，不做。

---

## 四、第三梯队：按需取用（4 项）

| # | 实践 | CRM 证据 | LiteShop 取用方式 |
|---|---|---|---|
| 1 | **useUpdateEffect**（跳过首次渲染的 useEffect，11 行） | useUpdateEffect.js:4-13 | 仅在出现 2~3 个稳定调用方后再进入 shared；否则留在具体 app，避免工具泛化 |
| 2 | **表格列宽持久化**：`onColumnsSettingChange(key, width)` 回调 + 800px 钳制上限 + localStorage 存储 | table-utils.js:126-148；lxtable/index.tsx:181-182 | admin 商品/订单列表可做；结合 2.4 的 storage 封装 |
| 3 | **分页 per_page 用户记忆**：按模块 localStorage 记住每页条数 | customer/list/index.jsx:208 | admin 列表体验项；记忆键 `['table-page-size', module, userId]` |
| 4 | **表格 Bridge 命令式 API**：`getTableBrige` 外抛 setLoading/changeRow/setScrollPosition | lxtable/index.tsx:187-260 | 用 React 18 标准的 `useImperativeHandle + forwardRef` 实现，不用回调外抛写法；admin 批量发货的"选中行→操作栏"联动 |

## 五、反面模式警示（不借鉴，引以为戒）

CRM 的技术债从反面印证了 LiteShop 现有规约的必要性：

| # | CRM 反面模式 | 证据 | 对 LiteShop 的印证 |
|---|---|---|---|
| 1 | **window 全局灰度变量泛滥**：13+ 个 `window.new_customer_modal` 开关，grep 命中 53 处、30 个文件；无类型、无追踪、无删除机制 | app.js:47-84 | 我们用 DB feature_flags 表（plan-12）是对的；任何灰度开关不得走 window |
| 2 | **巨型文件**：列表页 1428 行、筛选组件 1631 行、领域 service 1616 行 | customer/list/index.jsx 等 | 即我们 M1（api/admin.py 661 行）/ M3（page-builder 645 行）要拆的方向；组件/文件超 300 行就该警惕 |
| 3 | **新旧实现并存不清理**：同一列表页 index(1428 行)/index-new(1248 行)/index-dynamic(8 行) 三套；index-entry 里 import 了却不用，永远渲染 NewIndex | index-entry.jsx:6-11 | 即我们报告第八章 A 类死代码（17 个）；"兼容层必须定删除时间表"（第九章 P1-3）不是过度设计 |
| 4 | **组件库工程劣化**：全库 `props: any`、`export * from 'antd'`（宿主版本强耦合，admin 被迫锁死 lx-ui@1.0.26）、入口副作用（moment.locale/require css）、拷贝式迭代（`index 2 copy 2.tsx`） | lxComponent/src | shared-components 坚持 Props interface + peerDependencies + 纯组件（无副作用）；project-radar 重复检测正是拦"index 2 copy 2"这类文件 |
| 5 | **axios 实例各文件复制粘贴创建**：每个领域 service 重复 `createApi({...})`，token 模块加载时读一次，token 刷新后旧实例全部失效 | customer.js:12-20 vs common.js:10-30 | 单例 httpClient（service/http.ts）是对的；改造时保持单实例，只加拦截器逻辑（401 刷新/幂等键），不拆散 |

另有两个小教训值得记录：拦截器命中登出时 `return;`（不 resolve 不 reject，Promise 永久悬挂）——我们做 401 处理（C3）时要确保所有分支都有明确归宿；后端响应格式四分五裂导致前端公共层 if/else 兼容四种格式——契约统一（OpenAPI + ApiEnvelope）的价值所在。

---

## 六、落地路线图（与既有报告批次整合）

| 时机 | 内容 | 关联 |
|---|---|---|
| 随批次 2（前端交易链路修复） | 2.3 URL 字典 + fillPath 工具；2.4 storage 封装 | H3 幂等键改造同 PR |
| 随批次 3（工程卫生） | 3.2 shared-components 补 stories + prop 版本标注；3.3 通用件受控/非受控规范 | 第八章死代码清理后做 |
| plan-10（admin RBAC） | 2.1 权限快照数据流全套（扁平化/缓存校验/错峰刷新/useAccess） | M7 根治 |
| 随 M3（错误处理建模） | 2.2 错误码 → 缺省页映射表 | 与 error-codes.md 联动 |
| H6 UI 库决策后 | 3.1 token 单源桥接（CSS 变量 + ui-kit `--ui-*`） | M7 + H6 联动；依赖和宪法变更需先确认 |
| 部署脚本治理时（M10） | 3.4 版本目录 + current 指针 | 对齐部署发布规范 |
| 按需 | 第三梯队 4 项 | admin 列表迭代时顺带 |

## 七、与既有报告的交叉引用

| 借鉴项 | 既有报告编号 | 关系 |
|---|---|---|
| 2.1 权限快照数据流 | M7（RBAC 仅展示层） | 根治方案的前端数据流部分 |
| 2.2 错误码缺省页 | M3（错误处理未建模 ApiError） | M3 实施时的页面级消费方案 |
| 2.3 URL 字典 | H3（幂等键） | 同批改造 |
| 2.4 storage 封装 | — | 新增工具 |
| 3.1 token 双源 | M7（tokens 混乱）+ H6（UI 库，**已定 B**） | M7 修复为 ui-kit 前置项；token 桥接方案见《UI组件库设计方案.md》 |
| 3.2 组件文档 | 既有报告无（shared-components 零测试已提） | 补课 |
| 3.3 双模式组件协议 | — | shared-components 规范增强 |
| 3.4 版本目录 | M10（deploy.ps1 名实不符） | 部署脚本治理的配套 |
| 5.3 新旧并存 | 第八章 A 类死代码 | 反面印证 |

---

*本文档基于 2026-09-07 对 CRM 项目的代码快照分析生成；CRM 侧行号以当日文件为准。*
