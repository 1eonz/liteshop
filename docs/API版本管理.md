# LiteShop API 版本管理

> 本文件定义 LiteShop API 的版本演进、弃用策略、兼容窗口、破坏性变更流程。
> 配套 docs/CI-CD规范.md 的语义化版本规约。

---

## 一、版本号策略

### 1.1 URL 路径版本（主版本）

```
/api/v1/orders        # v1 主版本
/api/v2/orders        # v2 主版本（破坏性变更才升级）
```

- 主版本号（v1 / v2 / v3）反映**不兼容变更**
- 主版本升级是重大事件，需提前公告
- 同一时期最多 2 个主版本并存（如 v1 弃用期内 + v2 活跃）

### 1.2 语义化版本（包级别）

每个后端版本号 `v{MAJOR}.{MINOR}.{PATCH}`：

- MAJOR：API 破坏性变更（升 v2）
- MINOR：新增 API / 新增可选字段（向后兼容）
- PATCH：bug 修复（向后兼容）

### 1.3 何时升主版本

| 变更类型 | 升主版本？ | 示例 |
|---|---|---|
| 新增 API 端点 | ❌ | 新增 `/api/v1/refunds` |
| 新增响应字段 | ❌ | order 响应加 `coupon_id` |
| 新增可选请求参数 | ❌ | 查询参数加 `?sort=asc` |
| 删除 API 端点 | ✅ | 删 `/api/v1/legacy-search` |
| 删除响应字段 | ✅ | order 响应删 `legacy_status` |
| 改字段类型 | ✅ | `amount: string` → `amount: number` |
| 改必填参数 | ✅ | `phone` 从可选改必填 |
| 改枚举值 | ✅ | order status 从 5 个改 7 个 |
| 改业务语义 | ✅ | `price` 从分改元 |

---

## 二、弃用策略（Deprecation）

### 2.1 弃用流程

```
1. 标记 @Deprecated（代码 + OpenAPI 文档）
  ↓
2. API 响应加 Deprecation Header
  ↓
3. 公告（钉钉群 + 邮件 + CHANGELOG）
  ↓
4. 兼容期 90 天（minor 变更）/ 180 天（major 变更）
  ↓
5. 兼容期结束 → 下个主版本删除
```

### 2.2 HTTP 弃用 Header

弃用期内的 API 响应必须包含以下 Header：

```
Deprecation: true
Sunset: Wed, 09 Sep 2026 00:00:00 GMT    # 计划下线时间
Link: </api/v2/orders>; rel="successor-version"   # 替代 API
```

### 2.3 弃用告警

```python
# 弃用 API 被调用时记日志 + Prometheus 计数
@deprecated_api(route="/api/v1/legacy-search", sunset="2026-09-09")
async def legacy_search():
    log.warning("deprecated_api_called", api="/api/v1/legacy-search")
    deprecated_api_calls.labels(api="legacy-search").inc()
    # ... 业务逻辑
```

### 2.4 弃用追踪

监控指标 `liteshop_deprecated_api_calls_total{api="..."}`：

| 弃用 API 调用量 | 处理 |
|---|---|
| 持续 > 100/天 | 延长兼容期，主动联系调用方 |
| < 10/天 | 按计划下线 |
| 0/天 | 可提前下线 |

---

## 三、兼容窗口

### 3.1 兼容期长度

| 变更类型 | 兼容期 | 公告提前期 |
|---|---|---|
| 新增可选字段 | 0 | 无需公告 |
| 新增 API | 0 | 无需公告 |
| 删 API 端点 | 90 天 | 30 天 |
| 删响应字段 | 90 天 | 30 天 |
| 改字段类型 | 180 天 | 60 天 |
| 主版本升级 | 180 天 | 90 天 |

### 3.2 兼容期内的责任

- **提供方（backend）**：保持旧 API 可用，输出弃用 Header，追踪调用量
- **调用方（frontend / 第三方）**：在兼容期内迁移到新 API，不在旧 API 上新增功能

### 3.3 兼容期结束

- 下线前 7 天：再次公告（钉钉 + 邮件）
- 下线日：删除旧 API 端点
- 下线后：旧 API 返回 410 Gone + 引导信息

---

## 四、破坏性变更流程（升主版本）

### 4.1 决策与公告

```
1. 评估必要性（是否真的需要破坏性变更？）
2. 提交 RFC（变更原因 / 影响范围 / 迁移指南）
3. 用户确认
4. 提前 90 天公告（钉钉 + 邮件 + CHANGELOG + 文档）
```

### 4.2 实施步骤

```
Step 1：v1 API 标 deprecated（兼容期内保留）
  ↓
Step 2：v2 API 开发完成 + 测试
  ↓
Step 3：v1 + v2 并存（响应 Header 提示弃用）
  ↓
Step 4：调用方迁移到 v2
  ↓
Step 5：v1 调用量 < 阈值 → 下线
```

### 4.3 迁移指南模板

```markdown
# v1 → v2 迁移指南

## 变更摘要
- `price` 字段从 `string` 改为 `number`（整数分）
- `legacy_status` 字段删除，用 `status` 替代

## 迁移步骤
1. 把 `price: "19990"` 改为 `price: 19990`
2. 把 `legacy_status: "PENDING"` 改为 `status: "pending"`

## 兼容期
- v1 保留至 2026-12-09
- 期间 v1 响应包含 Deprecation Header

## 联系
迁移问题联系 @backend-team
```

---

## 五、OpenAPI 文档版本

### 5.1 多版本文档

```
docs/api-contracts/
└── v1/
    ├── orders.yaml           # v1（弃用期内）
    └── payments.yaml
docs/api-contracts/
└── v2/
    ├── orders.yaml           # v2（活跃）
    └── payments.yaml
```

### 5.2 文档变更日志

每个 OpenAPI 文件头部必须包含 `version` 和变更日志：

```yaml
openapi: 3.0.3
info:
  title: LiteShop Orders API
  version: 1.2.0
  description: |
    ## 变更日志
    - 1.2.0：新增 `coupon_id` 可选字段
    - 1.1.0：新增 `?sort=` 查询参数
    - 1.0.0：初始版本
```

---

## 六、前端 SDK 版本对齐

### 6.1 shared-types 与 API 版本绑定

`packages/shared-types/` 的版本号必须与 API 主版本对齐：

```
shared-types v1.x ↔ API v1
shared-types v2.x ↔ API v2
```

### 6.2 类型变更同步流程

详见 AGENTS.md §4.4 公共代码约束与兼容性管理。

```
API 字段变更
  ↓
OpenAPI 文档更新
  ↓
shared-types 更新（同 PR）
  ↓
前端代码迁移（同 PR 或后续 PR）
  ↓
CI 枚举同步校验
```

---

## 七、与 PRD/AGENTS.md 的对应

| 本文件章节 | 对应文档 |
|---|---|
| 版本号策略 | docs/CI-CD规范.md §五 版本号 Tag |
| 弃用策略 | PRD E7 接口契约补强 |
| 兼容窗口 | PRD D2.1 金额单位规约（已是破坏性设计，必须一次到位） |
| 破坏性变更流程 | AGENTS.md §8 人工介入红线 |
| shared-types 同步 | AGENTS.md §4.4 公共代码约束 |

---

## 八、project-radar 集成

project-radar skill 检测：
- API 路径是否有版本号（`/api/v1/`） → 无则 🟡
- 弃用 API 是否有 `Deprecation` Header → 无则 🟡
- 是否有 API 变更日志 → 无则 🟡
- 是否有迁移指南文档 → 无则 🟡
- shared-types 版本号是否与 API 主版本对齐 → 否则 🔴

---

**文件结束**

> API 版本管理不是技术问题，是契约问题。1a 期 MVP 阶段 API 还在迭代，不需要严格弃用流程，但要养成"破坏性变更必须公告 + 保留兼容期"的习惯。
> 记住：删 API 容易，迁移调用方难。
