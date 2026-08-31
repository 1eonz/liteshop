
### D2.3 i18n 国际化框架（D-21）

#### D2.3.1 语言包结构

```
packages/shared-types/src/locales/
├── zh-CN/              # 简体中文（默认）
│   ├── common.json
│   ├── errors.json
│   ├── auth.json
│   ├── product.json
│   ├── order.json
│   └── ...
├── en-US/              # 英文（二期）
│   └── ...
└── index.ts
```

#### D2.3.2 错误码 i18n 文件示例

```json
// packages/shared-types/src/locales/zh-CN/errors.json
{
  "errors": {
    "price_changed": "商品价格已变更，请重新确认",
    "stock_insufficient": "库存不足",
    "order_status_conflict": "订单状态冲突，请刷新后重试",
    "token_expired": "登录已过期，请重新登录",
    "permission_denied": "权限不足",
    "rate_limited": "请求过于频繁，请稍后重试"
  }
}
```

#### D2.3.3 前端 i18next 初始化

```typescript
// packages/h5-app/src/i18n.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCN from '@liteshop/shared-types/locales/zh-CN';

i18n.use(initReactI18next).init({
  resources: { 'zh-CN': zhCN },
  lng: 'zh-CN',
  fallbackLng: 'zh-CN',
  defaultNS: 'common',
  ns: ['common', 'errors', 'auth', 'product', 'order'],
  interpolation: { escapeValue: false },
});

export default i18n;
```

#### D2.3.4 错误码处理流程

```typescript
// packages/h5-app/src/api/interceptor.ts
import i18n from '@/i18n';

axios.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const apiError = err.response?.data;
    if (apiError?.i18nKey) {
      // 前端有翻译时用翻译，否则 fallback 到后端 message
      apiError.message = i18n.t(apiError.i18nKey, { defaultValue: apiError.message });
    }
    return Promise.reject(apiError);
  }
);
```

#### D2.3.5 后端 i18n

后端默认返回中文 message，i18nKey 字段同步返回。后端不主动 i18n，由前端根据 i18nKey 翻译。这样：
- 后端无需维护多语言文件
- 翻译集中在 shared-types/locales
- 后端 message 永远是中文兜底

### D2.4 统一枚举管理（D-05 通用化）

#### D2.4.1 shared-types 枚举目录

```
packages/shared-types/src/enums/
├── order.ts           # 订单状态、售后状态、售后类型
├── payment.ts         # 支付方式、支付状态
├── logistics.ts       # 物流公司
├── product.ts         # 商品状态、规格类型
├── stock.ts           # 库存变动类型
├── user.ts            # 用户角色、会员等级
├── notification.ts    # 通知渠道、通知状态
├── page.ts            # 页面类型、组件类型
└── index.ts
```

#### D2.4.2 后端枚举同步

```python
# backend/app/enums.py
from enum import StrEnum

class OrderStatus(StrEnum):
    PENDING_PAYMENT = 'PENDING_PAYMENT'
    PAID = 'PAID'
    SHIPPED = 'SHIPPED'
    COMPLETED = 'COMPLETED'
    CANCELLED = 'CANCELLED'

class AfterSaleStatus(StrEnum):
    PENDING_REVIEW = 'PENDING_REVIEW'
    APPROVED = 'APPROVED'
    REJECTED = 'REJECTED'
    GOODS_RETURNED = 'GOODS_RETURNED'
    REFUNDING = 'REFUNDING'
    REFUNDED = 'REFUNDED'
    REFUND_FAILED = 'REFUND_FAILED'
    CLOSED = 'CLOSED'

class AfterSaleType(StrEnum):
    REFUND_ONLY = 'REFUND_ONLY'
    REFUND_AND_RETURN = 'REFUND_AND_RETURN'
    EXCHANGE = 'EXCHANGE'
```

#### D2.4.3 枚举同步 CI 校验

CI 跑脚本对比后端 `enums.py` 与前端 `enums/*.ts`，发现不一致阻止合并：

```python
# scripts/check_enum_sync.py
# 解析后端 StrEnum 与前端 TS const 对象，对比 key/value
```

### D2.5 通知中心契约（D-09）

#### D2.5.1 通知模板表

```sql
CREATE TABLE notification_templates (
    id              BIGSERIAL PRIMARY KEY,
    key             VARCHAR(100) NOT NULL UNIQUE,   -- 'order_paid', 'order_shipped'
    name            VARCHAR(100) NOT NULL,
    event           VARCHAR(50) NOT NULL,           -- 'order.paid' / 'order.shipped' / 'form.submitted'
    channels        JSONB NOT NULL,                 -- ["sms", "email", "in_app", "wechat"]
    title_template  VARCHAR(200),                    -- 标题模板（支持变量插值）
    body_template   TEXT NOT NULL,                   -- 正文模板
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### D2.5.2 通知记录表

```sql
CREATE TABLE notifications (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT,                          -- 接收用户（站内信用）
    template_key    VARCHAR(100) NOT NULL,
    channel         VARCHAR(20) NOT NULL,            -- sms / email / in_app / wechat
    title           VARCHAR(200),
    body            TEXT,
    target          VARCHAR(200),                    -- 手机号/邮箱/用户ID/openid
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING / SENT / FAILED
    error_message   TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_status ON notifications(status);
```

#### D2.5.3 通知发送流程

```
业务事件（如 order.paid）
       ↓
  发事件到 Redis Stream：notification:events
       ↓
Celery worker 消费
       ↓
  查 notification_templates（event='order.paid', enabled=true）
       ↓
  按模板 channels 配置，逐渠道发送
       ↓
  写 notifications 记录（每渠道一条）
       ↓
  失败重试 3 次，间隔指数退避
       ↓
  3 次失败标 FAILED，后台告警
```

#### D2.5.4 预置通知事件

| event | 模板 key | 渠道 | 触发时机 |
|---|---|---|---|
| `order.paid` | order_paid | sms + in_app | 用户支付成功 |
| `order.shipped` | order_shipped | sms + in_app | 后台发货 |
| `order.completed` | order_completed | in_app | 用户确认收货 |
| `order.cancelled` | order_cancelled | in_app | 订单取消 |
| `after_sale.reviewed` | after_sale_reviewed | sms + in_app | 售后审核结果 |
| `after_sale.refunded` | after_sale_refunded | sms + in_app | 退款成功 |
| `stock.warning` | stock_warning | in_app + email | 库存低于阈值（后台） |
| `form.submitted` | form_submitted | email | 官网表单提交（通知商家） |
| `user.registered` | user_registered | sms | 新用户注册（欢迎） |

#### D2.5.5 通知 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/notifications | 站内信列表（分页、未读优先） |
| GET | /api/notifications/unread-count | 未读数量 |
| PUT | /api/notifications/{id}/read | 标记已读 |
| PUT | /api/notifications/read-all | 全部已读 |
| GET | /api/admin/notification-templates | 模板列表 |
| PUT | /api/admin/notification-templates/{id} | 编辑模板（启用/禁用/改文案） |

### D2.6 限流策略（D-28）

#### D2.6.1 限流维度与阈值

| 接口 | 维度 | 阈值 | 算法 |
|---|---|---|---|
| POST /api/auth/sms-code | 手机号 | 1 次/60s，5 次/天 | 滑动窗口 |
| POST /api/auth/sms-code | IP | 10 次/小时 | 滑动窗口 |
| POST /api/auth/login | 用户名 | 5 次/5 分钟 | 滑动窗口 |
| POST /api/auth/login | IP | 50 次/分钟 | 滑动窗口 |
| POST /api/orders | 用户 | 10 次/分钟 | 滑动窗口 |
| POST /api/orders | IP | 100 次/分钟 | 滑动窗口 |
| POST /api/form-submissions | IP | 5 次/分钟 | 滑动窗口 |
| POST /api/form-submissions | 邮箱 | 1 次/分钟 | 滑动窗口 |
| 默认（其他接口） | 用户 | 1000 次/分钟 | 滑动窗口 |
| 默认（其他接口） | IP | 200 次/分钟 | 滑动窗口 |

#### D2.6.2 Redis ZSET 滑动窗口实现

```python
# backend/app/core/rate_limiter.py
import time
import redis.asyncio as redis

async def rate_limit(key: str, max_count: int, window_sec: int):
    """滑动窗口限流，超限抛 RATE_LIMITED"""
    now = time.time()
    window_start = now - window_sec
    r = redis.from_url(REDIS_URL)

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)   # 清理过期记录
    pipe.zadd(key, {str(now): now})               # 加入当前请求
    pipe.zcard(key)                                # 统计窗口内数量
    pipe.expire(key, window_sec)                   # 设置 key 过期
    _, _, count, _ = await pipe.execute()

    if count > max_count:
        raise ApiError(
            code=42900,
            i18nKey='common.rate_limited',
            message='请求过于频繁，请稍后重试'
        )
```

#### D2.6.3 限流响应

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60
Content-Type: application/json

{
  "code": 42900,
  "message": "请求过于频繁，请稍后重试",
  "i18nKey": "common.rate_limited",
  "requestId": "req_abc123"
}
```

### D2.7 健康检查（D-27 之一）

#### D2.7.1 分层探针

| 路径 | 用途 | 检查项 |
|---|---|---|
| `/health` | 存活探针（Liveness） | 进程是否在（直接返回 200） |
| `/ready` | 就绪探针（Readiness） | DB 连通 + Redis 连通 + OSS 可达 |
| `/metrics` | Prometheus 指标 | 请求量/延迟/错误率/业务指标 |

#### D2.7.2 /ready 实现

```python
# backend/app/api/health.py
from fastapi import APIRouter, Response
from app.core.db import check_db
from app.core.redis import check_redis
from app.core.oss import check_oss

router = APIRouter()

@router.get('/ready')
async def ready(response: Response):
    checks = {
        'db': await check_db(),
        'redis': await check_redis(),
        'oss': await check_oss(),
    }
    all_ok = all(checks.values())
    response.status_code = 200 if all_ok else 503
    return {
        'status': 'ok' if all_ok else 'degraded',
        'checks': checks,
        'timestamp': datetime.utcnow().isoformat()
    }
```

#### D2.7.3 Prometheus 指标

```
# /metrics 输出（Prometheus 格式）
http_requests_total{method="GET",path="/api/products",status="200"} 12345
http_request_duration_seconds_bucket{path="/api/products",le="0.1"} 11000
liteshop_orders_total{status="paid"} 500
liteshop_stock_locked_total 1200
liteshop_payment_callback_total{channel="wechat",result="success"} 480
```

### D2.8 API 版本策略

- 路径前缀：`/api/v1/...`
- 破坏性变更升版本号 `/api/v2/...`，v1 保留至少 6 个月
- OpenAPI 文件按版本组织：`docs/api-contracts/v1/*.yaml`

---

## D3. 低代码 Schema 版本管理与缓存策略

### D3.1 ComponentSchema 版本字段（D-06）

#### D3.1.1 Schema 结构修订

在 v1.1 第三章 3.4 的 `ComponentSchema` 基础上新增 `version` 字段：

```typescript
// packages/shared-types/src/schema.ts
interface ComponentSchema {
  id: string;
  type: string;                   // 组件类型，如 'product-grid'
  version: number;                // v1.2 新增：组件 Schema 版本，默认 1
  props: Record<string, any>;
  style: ContainerStyle;
  elementStyle?: ElementStyle;
  animation?: ComponentAnimation; // 仅官网组件
}

interface PageSchema {
  schemaVersion: number;          // v1.2 新增：页面 Schema 整体版本
  pageStyle: PageStyle;
  seo?: PageSEO;
  animation?: PageAnimation;
  components: ComponentSchema[];
}
```

#### D3.1.2 迁移函数注册表

```typescript
// packages/shared-components/src/migrations/registry.ts

type MigrationFn = (oldSchema: any) => any;

interface MigrationRegistration {
  componentType: string;
  migrations: MigrationFn[]; // migrations[0] = v1→v2, migrations[1] = v2→v3
}

const migrationRegistry: Record<string, MigrationRegistration> = {
  'product-grid': {
    migrations: [
      // v1 → v2：字段重命名
      (old) => ({
        ...old,
        version: 2,
        props: {
          ...old.props,
          // v1 的 cols → v2 的 columns
          columns: old.props.cols ?? 2,
          cols: undefined,
        }
      }),
    ]
  },
  'hero': {
    migrations: [
      // v1 → v2：新增 animation 字段
      (old) => ({
        ...old,
        version: 2,
        animation: old.animation ?? { enabled: false, type: 'fade-up' }
      })
    ]
  }
};

export function migrateComponent(schema: ComponentSchema): ComponentSchema {
  const reg = migrationRegistry[schema.type];
  if (!reg) return schema;

  let current = schema;
  while (current.version < reg.migrations.length + 1) {
    const migrateFn = reg.migrations[current.version - 1];
    current = migrateFn(current);
  }
  return current;
}
```

#### D3.1.3 渲染前迁移

```typescript
// packages/shared-components/src/SchemaRenderer.tsx
import { migrateComponent } from './migrations/registry';

export function SchemaRenderer({ schema }: { schema: PageSchema }) {
  return (
    <div style={schema.pageStyle}>
      {schema.components.map((comp) => {
        // 渲染前迁移到最新版本
        const latestSchema = migrateComponent(comp);
        const Comp = componentMap[latestSchema.type];
        if (!Comp) {
          console.warn(`Component type "${latestSchema.type}" not registered`);
          return null;
        }
        return (
          <div key={latestSchema.id} style={latestSchema.style}>
            <Comp {...latestSchema.props} elementStyle={latestSchema.elementStyle} />
          </div>
        );
      })}
    </div>
  );
}
```

#### D3.1.4 版本管理规约

- **存储时保留原版本**：DB 存商家保存的 schema 原样（含原 version）
- **渲染时迁移到最新**：SchemaRenderer 渲染前统一 migrate
- **迁移函数只增不改**：迁移函数不可逆，新增字段设默认值，重命名映射到新字段
- **不迁移场景**：低版本 schema 在编辑器中打开时，编辑器加载最新组件定义，自然写入新版本

### D3.2 Schema 缓存策略（D-07）

#### D3.2.1 Cache-Aside + 事件失效

```
读流程（Next.js SSG / H5 启动时）：
  1. 查 Redis：page:schema:{page_id}
  2. hit → 返回
  3. miss → 查 DB → 回填 Redis（TTL 1h）→ 返回

写流程（后台保存页面）：
  1. 写 DB（pages.schema = new_schema）
  2. 发 page.updated 事件到 Redis Stream
  3. Celery worker 消费：
     a. 删 Redis：DEL page:schema:{page_id}
     b. 触发 ISR revalidate（官网）
     c. 触发 H5 Service Worker 通知（通过 SSE 推送 version 变化）
```

#### D3.2.2 事件结构

```typescript
// Redis Stream：page:events
{
  event: 'page.updated',        // page.updated / page.created / page.deleted
  pageId: '123',
  pageType: 'h5' | 'site',
  slug: 'home',
  version: 5,                   // page schema version（递增）
  timestamp: 1693526400
}
```

#### D3.2.3 Celery worker 处理

```python
# backend/app/page/events.py
from celery import Celery

app = Celery('liteshop', broker=REDIS_URL)

@app.task(bind=True, max_retries=3)
def handle_page_updated(self, event: dict):
    page_id = event['pageId']
    page_type = event['pageType']
    slug = event['slug']

    try:
        # 1. 删 Redis 缓存
        await redis.delete(f'page:schema:{page_id}')

        # 2. 官网页面：触发 ISR revalidate
        if page_type == 'site':
            await trigger_isr_revalidate(slug)

        # 3. H5 页面：通过 SSE 通知在线客户端
        if page_type == 'h5':
            await sse_notify('page:updated', {'pageId': page_id, 'version': event['version']})

    except Exception as e:
        # 指数退避重试：10s, 60s, 300s
        retry_in = [10, 60, 300][min(self.request.retries, 2)]
        raise self.retry(exc=e, countdown=retry_in)
```

#### D3.2.4 死信队列

3 次重试都失败的消息进入死信队列 `page:events:dead`，后台看板显示"ISR 同步失败"列表，人工介入。

#### D3.2.5 一致性保证

- 写 DB 与发事件用 **事务性发件箱（Transactional Outbox）**：先写 DB + outbox 表，再由独立 worker 读 outbox 发 Redis Stream，避免 DB 写成功但事件丢失
- ISR revalidate 失败时 SSG 页面保持上一次成功的静态内容（Next.js 天然支持），用户看到的是"上一版本"，不影响可用性
- H5 客户端收到 version 变化通知后，重新拉取 Schema 并渲染，期间显示旧版本

### D3.3 撤销重做与自动保存解耦

#### D3.3.1 状态分离

撤销栈管理"编辑中的内存状态"，自动保存只存"最后一次稳定态快照"：

```
[撤销栈]  ←→  [当前编辑态]  →  [自动保存触发]  →  [DB 最新稳定态]
   50 步         内存                     每 30s 或失焦
```

- 撤销栈：内存中的 Schema 快照数组，最多 50 步，Ctrl+Z/Ctrl+Y 操作栈
- 当前编辑态：用户正在编辑的 Schema（撤销栈栈顶）
- 自动保存：定时器触发，把当前编辑态写到 DB（不影响撤销栈）
- 自动保存失败：Toast 提示"保存失败"，撤销栈不变，用户可继续编辑或手动保存

#### D3.3.2 实现要点

```typescript
// packages/admin-app/src/builder/history.ts
import { useState, useCallback } from 'react';
import { produce } from 'immer';

const MAX_HISTORY = 50;

export function useSchemaHistory(initial: PageSchema) {
  const [past, setPast] = useState<PageSchema[]>([]);
  const [present, setPresent] = useState<PageSchema>(initial);
  const [future, setFuture] = useState<PageSchema[]>([]);

  const commit = useCallback((updater: (draft: PageSchema) => void) => {
    setPast(prev => {
      const newPast = [...prev, present].slice(-MAX_HISTORY);
      setPresent(produce(present, updater));
      setFuture([]);
      return newPast;
    });
  }, [present]);

  const undo = useCallback(() => {
    setPast(prev => {
      if (prev.length === 0) return prev;
      const previous = prev[prev.length - 1];
      setFuture(f => [present, ...f]);
      setPresent(previous);
      return prev.slice(0, -1);
    });
  }, [present]);

  const redo = useCallback(() => {
    setFuture(f => {
      if (f.length === 0) return f;
      const next = f[0];
      setPast(p => [...p, present]);
      setPresent(next);
      return f.slice(1);
    });
  }, [present]);

  return { present, commit, undo, redo, canUndo: past.length > 0, canRedo: future.length > 0 };
}
```

### D3.4 A/B 测试支持（D-30）

#### D3.4.1 多版本 Schema

```sql
CREATE TABLE page_variants (
    id          BIGSERIAL PRIMARY KEY,
    page_id     BIGINT NOT NULL REFERENCES pages(id),
    variant_key VARCHAR(10) NOT NULL,             -- 'A' / 'B' / 'C'
    schema      JSONB NOT NULL,
    traffic_pct INTEGER NOT NULL DEFAULT 0,        -- 0-100，流量占比
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(page_id, variant_key)
);
```

#### D3.4.2 分流逻辑

```typescript
// H5 端获取页面 Schema
async function getPageSchema(pageId: number, userId?: string) {
  const res = await api.get(`/api/pages/${pageId}/schema`, {
    params: { userId }  // 用于稳定分流
  });
  return res.data;
  // 后端逻辑：
  // 1. 查该 page 的所有 enabled variants
  // 2. 按 traffic_pct 加权随机（用 userId hash 保证稳定分流）
  // 3. 返回选中的 variant schema
}
```

#### D3.4.3 转化率上报

```typescript
// H5 端：用户完成关键动作（如下单）时上报
async function reportConversion(pageId: number, variantKey: string, eventType: string) {
  await api.post('/api/analytics/conversion', {
    pageId, variantKey, eventType, timestamp: Date.now()
  });
}
```

---

## D4. 架构与性能详细设计

### D4.1 H5 Schema 多级缓存（D-12）

#### D4.1.1 缓存层级

```
┌─────────────────────────────────────────────┐
│ L1: 内存（React Query 缓存）  ~0ms           │
├─────────────────────────────────────────────┤
│ L2: Service Worker + IndexedDB  ~10ms        │
├─────────────────────────────────────────────┤
│ L3: Redis（CDN 边缘缓存）    ~50ms           │
├─────────────────────────────────────────────┤
│ L4: PostgreSQL（源头）      ~100ms           │
└─────────────────────────────────────────────┘
```

#### D4.1.2 Service Worker 实现

```typescript
// packages/h5-app/src/sw.ts
import { clientsClaim } from 'workbox-core';
import { registerRoute } from 'workbox-routing';
import { StaleWhileRevalidate } from 'workbox-strategies';
import { CacheFirst } from 'workbox-strategies';

// Schema 接口：StaleWhileRevalidate（先返回缓存，后台更新）
registerRoute(
  ({ url }) => url.pathname.startsWith('/api/pages/') && url.pathname.endsWith('/schema'),
  new StaleWhileRevalidate({
    cacheName: 'page-schema',
    plugins: [{
      // 缓存中保存版本号，便于对比
      cacheWillUpdate: async ({ response }) => {
        const version = response.headers.get('x-schema-version');
        if (version) {
          const blob = await response.clone().blob();
          return new Response(blob, {
            status: response.status,
            statusText: response.statusText,
            headers: {
              ...response.headers,
              'x-schema-version': version,
            }
          });
        }
        return response;
      }
    }]
  })
);

// 静态资源（JS/CSS/图片）：CacheFirst
registerRoute(
  ({ url }) => url.origin === self.location.origin,
  new CacheFirst({ cacheName: 'static' })
);

clientsClaim();
```

#### D4.1.3 启动时序

```
1. App 启动
2. 同步从 SW 缓存读 Schema → 立即渲染首屏（< 100ms）
3. 并发 fetch 最新 Schema（带版本号 header）
4. 若版本号不同 → 替换 Schema → 重渲染（用户无感）
5. 若相同 → 跳过
```

```typescript
// packages/h5-app/src/hooks/usePageSchema.ts
import { useQuery } from '@tanstack/react-query';

export function usePageSchema(pageId: number) {
  return useQuery({
    queryKey: ['pageSchema', pageId],
    queryFn: async () => {
      const res = await api.get(`/api/pages/${pageId}/schema`);
      return res.data;
    },
    staleTime: 5 * 60 * 1000,  // 5 分钟内不重新拉
    // React Query 提供 L1 内存缓存
  });
}
```

#### D4.1.4 SSE 主动推送

```typescript
// packages/h5-app/src/sse.ts
const evtSource = new EventSource('/api/sse/page-updates');

evtSource.addEventListener('page:updated', (event) => {
  const { pageId, version } = JSON.parse(event.data);
  // 强制 refetch 该页面的 Schema
  queryClient.invalidateQueries({ queryKey: ['pageSchema', pageId] });
});
```

### D4.2 ISR revalidate 事件链路（D-13）

#### D4.2.1 整体链路

```
后台保存页面
    ↓
  写 DB + 写 outbox 表（同一事务）
    ↓
  Outbox worker 轮询 outbox 表
    ↓
  发 Redis Stream：page:events
    ↓
  Celery worker 消费
    ↓
  1. 删 Redis 缓存 page:schema:{id}
  2. 调 Next.js revalidate API
       ↓
     Next.js 收到 → 调 revalidatePath('/slug')
       ↓
     Next.js 后台重新生成该页面静态 HTML
       ↓
     成功 → 替换静态文件
     失败 → 保留上一版静态文件（不阻塞）
    ↓
  3. 3 次失败 → 进死信队列 + 后台告警
```

#### D4.2.2 Next.js revalidate API

```typescript
// packages/site-app/app/api/revalidate/route.ts
import { revalidatePath } from 'next/cache';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(req: NextRequest) {
  const token = req.headers.get('x-revalidate-token');
  if (token !== process.env.REVALIDATE_TOKEN) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { slug } = await req.json();
  revalidatePath(`/${slug}`);
  return NextResponse.json({ revalidated: true, now: Date.now() });
}
```

#### D4.2.3 后端调用

```python
# backend/app/page/isr.py
import httpx
from app.core.config import settings

async def trigger_isr_revalidate(slug: str):
    """触发 Next.js 重新生成指定页面"""
    url = f"{settings.NEXTJS_BASE_URL}/api/revalidate"
    headers = {'x-revalidate-token': settings.REVALIDATE_TOKEN}
    payload = {'slug': slug}

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
    return True
```

#### D4.2.4 事务性发件箱

```sql
CREATE TABLE outbox_events (
    id              BIGSERIAL PRIMARY KEY,
    event_type      VARCHAR(50) NOT NULL,         -- 'page.updated'
    payload         JSONB NOT NULL,
    published       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at    TIMESTAMPTZ
);

CREATE INDEX idx_outbox_unpublished ON outbox_events(id) WHERE published = FALSE;
```

```python
# backend/app/page/service.py
async def save_page(page_id: int, schema: dict, user_id: int):
    async with db.transaction():
        # 同一事务写 DB + outbox
        await page_repo.update(page_id, schema)
        await outbox_repo.create({
            'event_type': 'page.updated',
            'payload': {'pageId': page_id, 'slug': ..., 'pageType': ...}
        })
    # 事务成功后，outbox worker 异步发送到 Redis Stream
```

### D4.3 Vite + Next.js 双构建兼容（D-14）

#### D4.3.1 共享组件规范

1. **全部 "use client"**：shared-components 所有组件顶部加 `"use client"`，保证 Next.js App Router 能直接消费
2. **禁用构建专有 API**：不用 `import.meta.env`（Vite）、`process.env`（Next.js），环境差异通过 props 传入
3. **构建产物**：tsup 打包为 ESM + CJS 双格式

```typescript
// packages/shared-components/tsup.config.ts
import { defineConfig } from 'tsup';

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm', 'cjs'],
  dts: true,
  clean: true,
  external: ['react', 'react-dom'],
});
```

#### D4.3.2 CSS 处理

- 共享 CSS 通过 `shared-tokens` 包提供（CSS 变量 + Tailwind 配置）
- Vite 端：`import '@liteshop/shared-tokens/styles.css'`
- Next.js 端：在 `app/globals.css` 用 `@import` 引入，或通过 `next-global-css` 处理

#### D4.3.3 双构建 e2e 烟雾测试

```typescript
// packages/shared-components/tests/e2e/dual-build.test.ts
import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { ProductGrid } from '../../src';

describe('Component dual-build compatibility', () => {
  it('renders in Vite-style environment', () => {
    const { container } = render(<ProductGrid products={[]} />);
    expect(container.firstChild).toBeTruthy();
  });

  it('renders with "use client" directive', async () => {
    // 模拟 Next.js 环境：动态 import 检查 "use client" 标注
    const moduleSource = await fs.readFile('src/index.ts', 'utf-8');
    expect(moduleSource).toMatch(/"use client"/);
  });
});
```

CI 矩阵：

```yaml
# .github/workflows/ci.yml
jobs:
  shared-components-test:
    strategy:
      matrix:
        consumer: [vite, nextjs]
    steps:
      - run: pnpm --filter shared-components test
      - run: pnpm --filter shared-components run test:e2e:${{ matrix.consumer }}
```

### D4.4 3D 隔离方案（D-15）

#### D4.4.1 包结构

- `shared-components`：商城 + 官网共享组件，**不包含 3D**
- `shared-3d-components`：3D 组件独立包，**不进 componentMap 默认注册**

#### D4.4.2 按需加载

```typescript
// packages/site-app/app/pages/[slug]/page.tsx
import dynamic from 'next/dynamic';
import { SchemaRenderer, componentMap } from '@liteshop/shared-components';

// 3D 组件按需注册（仅在页面包含 3D 组件时）
const Hero3D = dynamic(() => import('@liteshop/shared-3d-components').then(m => m.Hero3D), {
  ssr: false,
  loading: () => <div>3D 加载中...</div>
});

function Page({ schema }) {
  const has3D = schema.components.some(c => c.type === 'hero-3d');
  const finalMap = has3D ? { ...componentMap, 'hero-3d': Hero3D } : componentMap;
  return <SchemaRenderer schema={schema} componentMap={finalMap} />;
}
```

#### D4.4.3 移动端降级

```typescript
// packages/shared-3d-components/src/detect.ts
export function shouldUse3D(): boolean {
  if (typeof navigator === 'undefined') return false;
  const cores = navigator.hardwareConcurrency || 0;
  const memory = (navigator as any).deviceMemory || 0;
  const isMobile = /Android|iPhone|iPad/i.test(navigator.userAgent);
  return cores >= 4 && memory >= 4 && !isMobile;
}
```

3D 组件内部检测：若 `shouldUse3D()` 为 false，渲染降级 2D 图/视频。

### D4.5 多租户独立部署（D-17）

#### D4.5.1 一期架构

一期为单店部署，每个商家独立 Docker Compose 实例：

```
商家 A：
  - PostgreSQL（独立库 liteshop_a）
  - Redis（独立 DB 0-15）
  - FastAPI（独立容器）
  - H5 + Admin（CDN）

商家 B：
  - PostgreSQL（独立库 liteshop_b）
  - Redis（独立 DB 0-15）
  - FastAPI（独立容器）
  - H5 + Admin（CDN）
```

#### D4.5.2 三期 SaaS 化路径

若三期要做共享 DB 多租户，按以下路径迁移：

1. 所有业务表加 `tenant_id BIGINT NOT NULL DEFAULT 0`
2. ORM 层加 `current_tenant_id` 上下文（从 JWT 解析）
3. 所有查询自动加 `WHERE tenant_id = :current_tenant_id`
4. 历史数据 `tenant_id = 0` 表示平台主账号，单独迁移
5. 索引重建为 `(tenant_id, ...)` 复合索引

#### D4.5.3 控制面（可选三期）

三期可建独立的 SaaS 控制面（独立部署）：
- 管理各商家实例的创建、续费、配置
- 不直接访问商家业务 DB，通过各商家 API 管理
- 商家数据物理隔离，故障半径小

### D4.6 商城与官网主题统一（D-29 续）

#### D4.6.1 主题数据流

```
后台主题配置页
  ↓ 写 site_themes 表
后端 GET /api/settings/theme?scope=h5|site|global
  ↓ 返回 [{ key: '--color-primary', value: '#ff6b6b' }, ...]
前端启动时拉取
  ↓
document.documentElement.style.setProperty(key, value)
  ↓
全站 CSS 变量生效
```

#### D4.6.2 主题变更实时预览

后台主题配置页改色时：
1. 本地 `style.setProperty` 即时预览
2. 保存时调 `/api/admin/settings/theme`，写 DB
3. 发 `theme.updated` 事件 → 通知所有在线 H5/官网客户端（SSE）→ 客户端重新拉取主题

---

## D5. 安全合规详细设计

### D5.1 联系表单字段级加密（D-18）

#### D5.1.1 加密策略

- 字段级 AES-256-GCM 加密
- 密钥通过云厂商 KMS（阿里云 KMS / 腾讯云 KMS）管理
- 应用启动时从 KMS 获取数据密钥，缓存在内存（每 24h 轮换）
- 密文存 DB，明文不入库不入日志

#### D5.1.2 表结构

```sql
CREATE TABLE form_submissions (
    id              BIGSERIAL PRIMARY KEY,
    form_id         VARCHAR(50) NOT NULL,           -- 表单 ID（后台配置）
    page_slug       VARCHAR(100),
    -- 加密字段（密文 + IV + tag）
    name_encrypted  BYTEA,
    phone_encrypted BYTEA,
    email_encrypted BYTEA,
    message_encrypted BYTEA,
    -- 非敏感字段明文
    company         VARCHAR(200),
    user_ip         INET,
    user_agent      TEXT,
    -- 元数据
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING / READ / PROCESSED
    processed_by    BIGINT REFERENCES admins(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL  -- 90 天后自动删除
);

CREATE INDEX idx_form_submissions_status ON form_submissions(status);
CREATE INDEX idx_form_submissions_expires ON form_submissions(expires_at);
```

#### D5.1.3 加密实现

```python
# backend/app/core/crypto.py
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64

class FieldEncryptor:
    def __init__(self, key: bytes):  # 32 bytes for AES-256
        self.aesgcm = AESGCM(key)

    def encrypt(self, plaintext: str) -> bytes:
        iv = os.urandom(12)
        ct = self.aesgcm.encrypt(iv, plaintext.encode('utf-8'), None)
        return iv + ct  # IV 前置

    def decrypt(self, data: bytes) -> str:
        iv, ct = data[:12], data[12:]
        return self.aesgcm.decrypt(iv, ct, None).decode('utf-8')

# 从 KMS 获取密钥（伪代码）
def get_data_key() -> bytes:
    kms = boto3.client('kms', region_name='cn-hangzhou')
    resp = kms.generate_data_key(KeyId=KMS_KEY_ID, KeySpec='AES_256')
    return resp['Plaintext']  # 32 bytes，仅在内存
```

#### D5.1.4 访问审计

```python
# backend/app/form/service.py
async def decrypt_form_submission(submission_id: int, admin_id: int) -> dict:
    # 记录访问日志
    await audit_log.record(
        admin_id=admin_id,
        action='form_submission.decrypt',
        resource_id=submission_id,
        ip=request.client.host
    )
    # 解密返回
    submission = await form_repo.get(submission_id)
    return {
        'name': encryptor.decrypt(submission.name_encrypted),
        'phone': encryptor.decrypt(submission.phone_encrypted),
        # ...
    }
```

#### D5.1.5 自动删除

```python
# backend/app/form/tasks.py
@celery.task
def cleanup_expired_submissions():
    """每天清理 90 天前的表单提交"""
    async def _cleanup():
        await form_repo.delete_expired()
    asyncio.run(_cleanup())
```

#### D5.1.6 被遗忘权

提供管理员接口 `DELETE /api/admin/form-submissions/{id}`，物理删除指定提交记录。

### D5.2 文件上传安全（D-20）

#### D5.2.1 白名单

| 文件用途 | 允许扩展名 | 允许 MIME | 大小限制 |
|---|---|---|---|
| 商品图/详情图 | jpg, png, webp | image/jpeg, image/png, image/webp | 5MB |
| 评价图 | jpg, png, webp | 同上 | 3MB |
| 视频组件 | mp4 | video/mp4 | 50MB |
| 3D 模型 | glb, gltf | model/gltf-binary, model/gltf+json | 10MB |
| 富文本附件 | pdf, doc, docx, xls, xlsx | application/pdf, ... | 10MB |

#### D5.2.2 双重校验

```python
# backend/app/upload/service.py
ALLOWED_MIME = {
    'image/jpeg', 'image/png', 'image/webp', 'video/mp4',
    'model/gltf-binary', 'model/gltf+json',
    'application/pdf'
}

MAGIC_NUMBERS = {
    b'\xff\xd8\xff': 'image/jpeg',                    # JPEG
    b'\x89PNG\r\n\x1a\n': 'image/png',                # PNG
    b'RIFF....WEBP': 'image/webp',                    # WebP
    b'\x00\x00\x00': 'video/mp4',                      # MP4 (简化判断)
    b'glTF': 'model/gltf-binary',                    # GLB
}

async def validate_file(file: UploadFile) -> bool:
    # 1. 扩展名校验
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS[ext]:
        raise ApiError(code=20701, message='文件类型不允许')

    # 2. MIME 校验（可伪造，仅第一道）
    if file.content_type not in ALLOWED_MIME:
        raise ApiError(code=20701, message='文件类型不允许')

    # 3. Magic Number 校验（读前 16 字节）
    head = await file.read(16)
    await file.seek(0)
    detected_mime = detect_mime_by_magic(head)
    if detected_mime != file.content_type:
        raise ApiError(code=20701, message='文件类型与扩展名不匹配')

    # 4. 大小校验
    if file.size > MAX_FILE_SIZE[ext]:
        raise ApiError(code=20702, message='文件大小超限')

    return True
```

#### D5.2.3 OSS 数据处理流水线

```
前端请求签名 → 后端校验 + 生成临时签名
       ↓
前端直传 OSS
       ↓
OSS 上传完成回调后端
       ↓
后端触发 OSS 数据处理：
  - 图片：转 WebP + 生成缩略图（OSS 数据处理服务）
  - 视频：截图首帧 + 转码
  - 模型：Draco 压缩
       ↓
更新 DB 文件记录（原 URL + 缩略图 URL + 处理状态）
```

#### D5.2.4 文件名安全化

```python
import uuid

def generate_safe_filename(original: str) -> str:
    """生成 UUID 文件名，原文件名存 metadata"""
    ext = original.rsplit('.', 1)[-1].lower()
    return f"{uuid.uuid4().hex}.{ext}"
```

### D5.3 支付环境隔离（D-19）

#### D5.3.1 环境变量分层

```bash
# .env.development（开发环境，提交到 git）
PAYMENT_MODE=sandbox
WECHAT_SANDBOX_MCH_ID=...
WECHAT_SANDBOX_API_KEY=...
WECHAT_SANDBOX_CERT_PATH=./certs/sandbox/
ALIPAY_SANDBOX_APP_ID=...
ALIPAY_SANDBOX_PRIVATE_KEY=...

# .env.staging（预发布环境，不提交到 git）
PAYMENT_MODE=sandbox
...

# .env.production（生产环境，不提交到 git，部署时注入）
PAYMENT_MODE=production
WECHAT_MCH_ID=...
WECHAT_API_KEY=...
WECHAT_CERT_PATH=/data/certs/production/
ALIPAY_APP_ID=...
ALIPAY_PRIVATE_KEY=...
```

#### D5.3.2 CI 防护

```yaml
# .github/workflows/security-check.yml
jobs:
  secret-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Detect production secrets in dev code
        run: |
          # 阻止生产密钥进 .env.development
          if grep -E 'MCH_ID=\d{10}|API_KEY=[a-f0-9]{32}' .env.development; then
            echo "生产支付密钥出现在开发环境配置文件！"
            exit 1
          fi
      - name: Detect secrets in code
        run: |
          # 阻止任何密钥进源码
          if grep -rE 'sk_live_|api_key.*=.*["\x27][a-f0-9]{32}' src/; then
            echo "源码中检测到密钥！"
            exit 1
          fi
```

### D5.4 a11y 合规（D-23）

#### D5.4.1 共享组件规范

```tsx
// packages/shared-components/src/Button/Button.tsx
export function Button({ children, variant, ...props }: ButtonProps) {
  return (
    <button
      type="button"
      aria-busy={props.loading}
      aria-disabled={props.disabled}
      className={cn(variantClasses[variant])}
      {...props}
    >
      {children}
    </button>
  );
}
// 禁止：<div onClick={...}> 模拟 button
```

#### D5.4.2 关键 a11y 检查项

| 检查项 | 规范 |
|---|---|
| 语义化标签 | 用 `<button>` `<a>` `<nav>` `<main>` `<article>` 等，禁止 `<div onClick>` 模拟交互 |
| 键盘导航 | Tab 可达，Enter/Esc 可触发，焦点可见（不滥用 `outline: none`） |
| ARIA | 动态组件（Dialog/Dropdown/Toast）完整标注 `role` `aria-expanded` `aria-hidden` |
| 对比度 | 文字与背景对比度 ≥ 4.5:1（普通文字）/ 3:1（大文字） |
| 图片 alt | 装饰图 `alt=""`，内容图描述性 alt |
| 表单 label | 每个输入框关联 `<label>` |
| 错误提示 | 表单错误用 `aria-invalid` + `aria-describedby` 关联错误信息 |

#### D5.4.3 CI 自动检测

```yaml
# .github/workflows/a11y.yml
jobs:
  axe-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm --filter shared-components run test:a11y
      - run: pnpm --filter h5-app run test:a11y
```

```typescript
// packages/shared-components/tests/a11y.test.ts
import { render } from '@testing-library/react';
import { AxePuppeteer } from '@axe-core/puppeteer';
import { ProductGrid } from '../src';

describe('a11y', () => {
  it('ProductGrid 无违规', async () => {
    const { container } = render(<ProductGrid products={[...]} />);
    const results = await new AxePuppeteer({ page }).analyze();
    expect(results.violations).toHaveLength(0);
  });
});
```

---

## D6. 新增功能详细设计

### D6.1 消息通知中心（D-09）

#### D6.1.1 渠道适配器

```python
# backend/app/notification/channels.py
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    @abstractmethod
    async def send(self, target: str, title: str, body: str) -> bool:
        ...

class SmsChannel(NotificationChannel):
    def __init__(self, sms_provider):  # aliyun/tencent
        self.provider = sms_provider

    async def send(self, phone: str, title: str, body: str) -> bool:
        try:
            await self.provider.send_sms(phone, body)
            return True
        except Exception as e:
            log.error(f'SMS send failed: {e}')
            return False

class EmailChannel(NotificationChannel):
    async def send(self, email: str, title: str, body: str) -> bool:
        ...

class InAppChannel(NotificationChannel):
    """站内信：写入 notifications 表，前端轮询/SSE 拉取"""
    async def send(self, user_id: str, title: str, body: str) -> bool:
        await notification_repo.create(user_id=int(user_id), title=title, body=body)
        # 推 SSE 通知
        await sse_notify(user_id, {'type': 'notification', 'title': title})
        return True

class WechatTemplateChannel(NotificationChannel):
    async def send(self, openid: str, title: str, body: str) -> bool:
        ...

CHANNEL_REGISTRY = {
    'sms': SmsChannel(sms_provider),
    'email': EmailChannel(),
    'in_app': InAppChannel(),
    'wechat': WechatTemplateChannel(),
}
```

#### D6.1.2 模板变量插值

```python
# backend/app/notification/template.py
import re

def render_template(template: str, context: dict) -> str:
    """变量插值：'订单 {order_no} 已支付' → context={'order_no': 'ABC123'}"""
    return re.sub(r'\{(\w+)\}', lambda m: str(context.get(m.group(1), '')), template)

# 示例
context = {'order_no': 'ABC123', 'amount': 1999, 'product_name': 'iPhone'}
title = render_template('支付成功', context)
body = render_template('您的订单 {order_no} 已支付 ¥{amount}', context)
# → '您的订单 ABC123 已支付 ¥1999'
```

#### D6.1.3 通知偏好设置

```sql
CREATE TABLE user_notification_preferences (
    user_id     BIGINT NOT NULL REFERENCES users(id),
    event       VARCHAR(50) NOT NULL,              -- 'order.paid', 'order.shipped'
    channels    JSONB NOT NULL,                     -- ["sms", "in_app"]，用户选择的渠道
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    PRIMARY KEY (user_id, event)
);
```

发送时优先取用户偏好，无偏好取模板默认渠道。

#### D6.1.4 站内信 UI

H5 端"我的消息"页：
- 列表：未读置顶 + 时间倒序
- 详情：标题 + 正文 + 时间
- 操作：标记已读、全部已读、按类型筛选

### D6.2 商品评价系统（D-10）

#### D6.2.1 表结构

```sql
CREATE TABLE reviews (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES products(id),
    order_item_id BIGINT NOT NULL REFERENCES order_items(id),  -- 关联订单项（防刷评）
    user_id     BIGINT NOT NULL REFERENCES users(id),
    rating      SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    content     TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    status      VARCHAR(20) NOT NULL DEFAULT 'PENDING',  -- PENDING / APPROVED / REJECTED
    admin_reply TEXT,
    replied_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(order_item_id)  -- 一个订单项只能评价一次
);

CREATE INDEX idx_reviews_product_id ON reviews(product_id) WHERE status = 'APPROVED';
CREATE INDEX idx_reviews_user_id ON reviews(user_id);

CREATE TABLE review_images (
    id          BIGSERIAL PRIMARY KEY,
    review_id   BIGINT NOT NULL REFERENCES reviews(id) ON DELETE CASCADE,
    url         VARCHAR(500) NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_review_images_review_id ON review_images(review_id);
```

#### D6.2.2 评价流程

```
1. 用户确认收货（order.status = COMPLETED）
2. 用户在订单详情点"评价"
3. H5 评价页：评分（1-5 星）+ 文字评价 + 图片上传（最多 5 张）
4. 提交：status = PENDING
5. 后台审核：
   - 敏感词过滤（自动）
   - 通过 → status = APPROVED，展示在商品详情
   - 拒绝 → status = REJECTED，通知用户修改
6. 后台可回复评价（admin_reply）
```

#### D6.2.3 商品详情评价展示

```typescript
// H5 端商品详情页评价区
GET /api/products/{productId}/reviews?page=1&size=10&sort=created_at:desc

// 返回结构
{
  list: [{
    id, rating, content, images: [{url}],
    user: { nickname, avatar },  // 匿名时返回 '匿名用户'
    adminReply, createdAt
  }],
  summary: {
    averageRating: 4.5,    // 平均评分
    totalCount: 128,        // 总评价数
    distribution: { 5: 80, 4: 30, 3: 10, 2: 5, 1: 3 }  // 各星级数量
  }
}
```

#### D6.2.4 防刷评

- 必须有有效订单（order_item_id 唯一约束）
- 必须订单状态为 COMPLETED
- 评价图片最多 5 张，单张 3MB
- 敏感词过滤（D6.1.3 提到的反垃圾模块复用）

### D6.3 搜索系统（一期 PG 全文索引）

#### D6.3.1 一期方案：PostgreSQL 全文索引

```sql
-- products 表增加全文索引字段
ALTER TABLE products ADD COLUMN search_vector tsvector;

-- 触发器自动维护
CREATE TRIGGER products_search_vector_trigger
BEFORE INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION
  tsvector_update_trigger(search_vector, 'pg_catalog.simple', name, description);

-- 中文分词扩展（需安装 pg_jieba 或 zhparser）
CREATE INDEX idx_products_search ON products USING GIN(search_vector);

-- 查询
SELECT * FROM products
WHERE search_vector @@ to_tsquery('pg_catalog.simple', 'iPhone & 手机')
ORDER BY ts_rank(search_vector, to_tsquery('iPhone & 手机')) DESC
LIMIT 20;
```

#### D6.3.2 搜索 API

```
GET /api/products/search?q=iPhone&page=1&size=20&sort=relevance

参数：
  q: 关键词
  sort: relevance / sales / price_asc / price_desc
  category_id: 可选分类筛选
  price_min, price_max: 可选价格区间

响应：同商品列表接口结构
```

#### D6.3.3 三期升级路径

三期接入 Meilisearch（轻量、自托管、性能好）：
1. 商品变更时同步到 Meilisearch 索引（通过 page.updated 类似事件）
2. 搜索 API 改为查 Meilisearch
3. 一期的 PG 全文索引保留作为 fallback

### D6.4 库存预警自动化（新增 3）

#### D6.4.1 预警配置

```sql
-- SKU 级安全库存
ALTER TABLE skus ADD COLUMN safety_stock INTEGER NOT NULL DEFAULT 10;

-- 全局默认安全库存（settings 表）
INSERT INTO settings (key, value) VALUES
('stock.default_safety_stock', '10'),
('stock.warning_enabled', 'true');
```

#### D6.4.2 预警触发

```python
# backend/app/stock/tasks.py
@celery.task
def check_stock_warning():
    """每小时检查库存预警"""
    threshold = int(settings.get('stock.default_safety_stock'))
    low_stock_skus = await sku_repo.find_low_stock(threshold)

    for sku in low_stock_skus:
        # 发 stock.warning 事件（通知中心订阅）
        event_bus.publish('stock.warning', {
            'skuId': sku.id,
            'productName': sku.product.name,
            'currentStock': sku.available_stock,
            'safetyStock': sku.safety_stock or threshold,
        })

    # 后台看板数据更新
    await cache.set('stock:warning_list', low_stock_skus, ttl=3600)
```

#### D6.4.3 补货建议

```python
# backend/app/stock/replenishment.py
async def get_replenishment_suggestions():
    """补货建议：基于销量 + 安全库存 + 采购周期"""
    suggestions = []
    for sku in await sku_repo.all():
        recent_sales = await get_recent_sales_30d(sku.id)
        daily_avg = recent_sales / 30
        lead_time = sku.supplier.lead_time_days if sku.supplier else 7
        suggested_qty = max(
            sku.safety_stock + daily_avg * lead_time - sku.available_stock,
            0
        )
        if suggested_qty > 0:
            suggestions.append({
                'skuId': sku.id,
                'productName': sku.product.name,
                'currentStock': sku.available_stock,
                'dailyAvgSales': daily_avg,
                'suggestedQty': int(suggested_qty)
            })
    return suggestions
```

### D6.5 运费模板（D-11）

#### D6.5.1 表结构

```sql
CREATE TABLE freight_templates (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    type        VARCHAR(20) NOT NULL,              -- WEIGHT / PIECE / REGION
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE freight_template_items (
    id              BIGSERIAL PRIMARY KEY,
    template_id     BIGINT NOT NULL REFERENCES freight_templates(id) ON DELETE CASCADE,
    region_codes    JSONB NOT NULL,               -- ["110000", "120000"] 省级编码
    first_unit      NUMERIC(10,2) NOT NULL,       -- 首重 kg / 首件数
    first_fee       INTEGER NOT NULL,               -- 首费（分）
    additional_unit NUMERIC(10,2) NOT NULL,         -- 续重 kg / 续件数
    additional_fee  INTEGER NOT NULL,               -- 续费（分）
    free_condition  JSONB,                          -- {"min_amount": 9900} 满多少包邮
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_freight_template_items_template_id ON freight_template_items(template_id);
```

#### D6.5.2 计费逻辑

```python
# backend/app/order/freight.py
from decimal import Decimal

async def calculate_freight(
    items: list[OrderItem],
    address: Address,
    template_id: int | None = None
) -> int:
    """计算运费（返回分）"""
    template = await freight_repo.get_template(template_id)
    if not template:
        return 0

    # 找到匹配的运费项（按收货地区）
    item = await freight_repo.find_item_by_region(template.id, address.province_code)
    if not item:
        return 0

    # 检查包邮条件
    if item.free_condition:
        min_amount = item.free_condition.get('min_amount', 0)
        if sum(i.total_amount for i in items) >= min_amount:
            return 0

    # 按类型计费
    if template.type == 'WEIGHT':
        total_weight = sum(i.weight * i.quantity for i in items)
        if total_weight <= item.first_unit:
            return item.first_fee
        extra = Decimal(str(total_weight - item.first_unit)) / item.additional_unit
        return item.first_fee + int(extra) * item.additional_fee

    elif template.type == 'PIECE':
        total_qty = sum(i.quantity for i in items)
        if total_qty <= int(item.first_unit):
            return item.first_fee
        extra = total_qty - int(item.first_unit)
        return item.first_fee + extra * item.additional_fee

    return item.first_fee
```

#### D6.5.3 API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /api/admin/freight-templates | 模板列表 |
| POST | /api/admin/freight-templates | 创建模板 |
| PUT | /api/admin/freight-templates/{id} | 编辑模板 |
| DELETE | /api/admin/freight-templates/{id} | 删除模板 |
| POST | /api/admin/freight-templates/{id}/items | 添加运费项 |
| PUT | /api/admin/freight-templates/{id}/items/{itemId} | 编辑运费项 |
| DELETE | /api/admin/freight-templates/{id}/items/{itemId} | 删除运费项 |
| POST | /api/orders/freight-calc | 计算运费（前端下单页用） |

### D6.6 优惠券预留（新增 6）

#### D6.6.1 一期预留

一期不实现优惠券，但在订单金额计算中预留字段：

```sql
-- orders 表已预留 discount_amount（见 D1.1.3）
-- order_items 表预留 discount_amount
ALTER TABLE order_items ADD COLUMN discount_amount INTEGER NOT NULL DEFAULT 0;

-- 二期实现时新增 coupons 表
-- coupon_users（用户优惠券）表
-- order_coupons（订单优惠券关联）表
```

#### D6.6.2 下单页 UI 预留

H5 订单确认页保留"优惠券"入口，灰色显示"暂未开放"：

```tsx
// packages/h5-app/src/pages/OrderConfirm.tsx
<div className="coupon-entry disabled">
  <span>优惠券</span>
  <span className="muted">暂未开放</span>
</div>
```

二期实现时改为可点击的优惠券选择器。

#### D6.6.3 计算函数预留

```typescript
// packages/shared-types/src/utils/order.ts
export interface OrderAmountBreakdown {
  productAmount: number;   // 商品总额（分）
  freightAmount: number;   // 运费（分）
  discountAmount: number;  // 优惠（分）一期固定 0
  totalAmount: number;     // 应付（分）
}

export function calculateOrderAmount(
  productAmount: number,
  freightAmount: number,
  discountAmount = 0  // 一期默认 0
): OrderAmountBreakdown {
  return {
    productAmount,
    freightAmount,
    discountAmount,
    totalAmount: productAmount + freightAmount - discountAmount,
  };
}
```

### D6.7 商品标签与推荐（新增 7）

#### D6.7.1 一期手动推荐

```sql
-- 商品关联推荐表
CREATE TABLE product_recommendations (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    recommended_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, recommended_id)
);

CREATE INDEX idx_product_recommendations_product_id ON product_recommendations(product_id);
```

#### D6.7.2 后台操作

商品编辑页"相关推荐"Tab：搜索商品 → 添加 → 排序。

#### D6.7.3 三期 AI 推荐

三期接入 AI 推荐服务（基于用户浏览/购买历史的协同过滤或向量检索）。

### D6.8 数据备份与恢复演练（新增 8）

#### D6.8.1 备份策略

```
每日全量备份（pg_dump）：
  - 时间：凌晨 3:00
  - 内容：全库 pg_dump + WAL 归档
  - 存储：OSS（加密 + 多区域复制）
  - 保留：7 天

WAL 归档：
  - 实时归档到 OSS
  - 支持时间点恢复（PITR）

每周备份验证：
  - 周日恢复到沙箱环境
  - 跑核心业务验证脚本
  - 记录恢复时间
```

#### D6.8.2 恢复演练

```bash
#!/bin/bash
# scripts/backup-restore-drill.sh
BACKUP_FILE=$(aws s3 ls s3://liteshop-backups/ | sort | tail -1 | awk '{print $4}')

# 1. 恢复到沙箱
docker run -d --name liteshop-restore-test -e POSTGRES_PASSWORD=test postgres:16
docker exec liteshop-restore-test pg_restore -U postgres -d liteshop < <(aws s3 cp s3://liteshop-backups/$BACKUP_FILE -)

# 2. 验证
docker exec liteshop-restore-test psql -U postgres -d liteshop -c "SELECT COUNT(*) FROM orders WHERE created_at::date = CURRENT_DATE - 1"

# 3. 记录恢复时间
echo "Restore completed at $(date)" >> /var/log/restore-drill.log
```

#### D6.8.3 演练计划

- 每月 1 日跑一次恢复演练
- 演练记录归档（恢复时间、数据完整性验证结果）
- 恢复时间目标 RTO < 30 分钟

---
