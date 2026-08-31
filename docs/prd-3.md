
## D7. 可观测性与 DevOps 详细设计

### D7.1 监控体系（D-27 之一）

#### D7.1.1 监控分层

```
┌──────────────────────────────────────────────┐
│ 应用层：Sentry（前端错误 + 后端异常）          │
├──────────────────────────────────────────────┤
│ 业务层：Prometheus + Grafana（业务指标）       │
├──────────────────────────────────────────────┤
│ 基础设施层：云监控（CPU/内存/磁盘/网络）       │
└──────────────────────────────────────────────┘
```

#### D7.1.2 业务指标清单

| 指标 | 类型 | 说明 |
|---|---|---|
| `liteshop_orders_total` | Counter | 订单创建总数（按状态） |
| `liteshop_order_amount_total` | Counter | 订单金额累计（分） |
| `liteshop_payment_callback_total` | Counter | 支付回调数（按渠道+结果） |
| `liteshop_stock_locked_total` | Gauge | 当前锁定库存 |
| `liteshop_cart_items_total` | Gauge | 当前购物车项数 |
| `liteshop_page_render_duration_seconds` | Histogram | 低代码页面渲染耗时 |
| `liteshop_isr_revalidate_total` | Counter | ISR revalidate 次数（按结果） |
| `http_requests_total` | Counter | HTTP 请求总数（按路径+状态） |
| `http_request_duration_seconds` | Histogram | HTTP 请求延迟 |

#### D7.1.3 web-vitals 上报

```typescript
// packages/site-app/src/lib/vitals.ts
import { getCLS, getFID, getLCP, getINP, getTTFB } from 'web-vitals';

function report(metric: any) {
  navigator.sendBeacon('/api/vitals', JSON.stringify({
    name: metric.name,
    value: metric.value,
    rating: metric.rating,
    page: location.pathname,
    ts: Date.now()
  }));
}

getCLS(report);
getFID(report);
getLCP(report);
getINP(report);
getTTFB(report);
```

### D7.2 Source Map 管理（D-26）

#### D7.2.1 构建配置

```typescript
// vite.config.ts / next.config.js
export default {
  build: {
    sourcemap: 'hidden',  // 生成但不引用
  }
};
```

#### D7.2.2 上传脚本

```bash
#!/bin/bash
# scripts/upload-sourcemaps.sh
VERSION=$(git rev-parse HEAD)

# 上传到私有 OSS bucket
find packages/*/dist -name "*.map" | while read f; do
  aws s3 cp "$f" "s3://liteshop-sourcemaps/$VERSION/$(basename $f)" \
    --acl private \
    --metadata "version=$VERSION,app=$(basename $(dirname $f))"
done

# 同时上传到 Sentry
sentry-cli sourcemaps upload --release="$VERSION" packages/*/dist
```

#### D7.2.3 Sentry release 关联

```bash
# 部署时关联 release
sentry-cli releases new "$VERSION"
sentry-cli releases set-commits "$VERSION" --auto
sentry-cli releases finalize "$VERSION"
sentry-cli releases deploys "$VERSION" new -e production
```

### D7.3 蓝绿部署（D-27）

#### D7.3.1 架构

```
                    ┌─ Nginx ─┐
                    │         │
            ┌───────┴──┐  ┌───┴───────┐
            │ Blue 环境 │  │ Green 环境 │
            │ (当前线上)│  │ (新版部署)  │
            └──────────┘  └───────────┘
```

#### D7.3.2 部署流程

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh
NEW_VERSION=$1

# 1. 部署到非活跃环境
docker-compose -f docker-compose.green.yml up -d --build

# 2. 健康检查
for i in {1..30}; do
  curl -f http://localhost:8001/ready && break
  sleep 2
done

# 3. 切换流量
sed -i 's/upstream_backend:8000/upstream_backend:8001/' nginx.conf
nginx -s reload

# 4. 观察 5 分钟
sleep 300

# 5. 关闭旧环境
docker-compose -f docker-compose.blue.yml down

# 6. 交换 blue/green 标签
mv docker-compose.green.yml docker-compose.blue.yml
```

#### D7.3.3 回滚

```bash
# 立即回滚（切回旧环境）
sed -i 's/upstream_backend:8001/upstream_backend:8000/' nginx.conf
nginx -s reload
```

### D7.4 数据库迁移回滚演练

#### D7.4.1 Alembic 规约

- 每个迁移必须有 `downgrade` 函数
- CI 跑 `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 验证可逆
- 涉及删列/改类型/数据回填的迁移，PR review 时必须人工确认

#### D7.4.2 回滚流程

```bash
# 1. 应用回滚到旧版本镜像
docker-compose up -d liteshop:$OLD_VERSION

# 2. 数据库迁移回滚
alembic downgrade -1

# 3. 验证
curl -f http://localhost:8000/health
```

### D7.5 CI 流水线（D-24）

#### D7.5.1 完整 CI 流程

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  # 1. Lint + 类型检查
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm lint            # ESLint + Prettier
      - run: pnpm typecheck       # tsc --noEmit
      - run: pnpm --filter backend run ruff-check
      - run: pnpm --filter backend run mypy

  # 2. 单元测试
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
      redis:
        image: redis:7
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm test --coverage
      - run: pnpm --filter backend run pytest --cov

  # 3. 构建
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm build
      - run: pnpm --filter backend run build

  # 4. 包体积门禁
  bundle-size:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm build
      - name: Analyze bundle size
        run: |
          SIZE=$(gzip -c packages/h5-app/dist/assets/*.js | wc -c)
          echo "H5 first screen JS gzip: ${SIZE} bytes"
          if [ $SIZE -gt 204800 ]; then  # 200KB
            echo "Bundle size exceeds 200KB limit!"
            exit 1
          fi

  # 5. a11y 检测
  a11y:
    runs-on: ubuntu-latest
    needs: build
    steps:
      - run: pnpm --filter shared-components run test:a11y
      - run: pnpm --filter h5-app run test:a11y

  # 6. OpenAPI 契约校验
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npx @stoplight/spectral-cli lint docs/api-contracts/v1/*.yaml

  # 7. 枚举同步检查
  enum-sync:
    runs-on: ubuntu-latest
    steps:
      - run: python scripts/check_enum_sync.py

  # 8. 安全扫描
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Secret scan
        run: |
          if grep -rE 'sk_live_|api_key.*=.*["\x27][a-f0-9]{32}' src/; then
            echo "Secrets detected in source code!"
            exit 1
          fi
```

#### D7.5.2 阻止合并规则

- 上述任一 job 失败 → 阻止合并到 main
- 首屏 JS gzip > 200KB → 阻止合并
- 枚举不一致 → 阻止合并
- OpenAPI lint 不通过 → 阻止合并

### D7.6 读写分离预留（D-25）

```python
# backend/app/core/db.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 一期：读写都指向主库
write_engine = create_async_engine(settings.DATABASE_URL)
read_engine = create_async_engine(settings.DATABASE_READ_URL or settings.DATABASE_URL)

# 二期：DATABASE_READ_URL 指向只读副本
# 三期：读写分离 + 多只读副本
```

---

## D8. 范围调整与排期修订

### D8.1 一期分阶段交付（D-16）

#### D8.1.1 1a 期：核心交易闭环（10 周）

目标：商家能开店、上架商品、用户能下单支付，跑通核心闭环。

| 阶段 | 周次 | 交付内容 |
|---|---|---|
| 基础架构 | 第 1-2 周 | Monorepo、shared-tokens、后端骨架、DB 设计、用户认证、OSS 上传、短信验证码、支付资质申请（D-19） |
| 商品与库存 | 第 3-4 周 | 商品分类/SPU/SKU 管理、库存三层模型+原子扣减、H5 商品浏览（分类/列表/详情/SKU 选择）、搜索 |
| 交易闭环 | 第 5-7 周 | 购物车（Redis+DB 双写 D-03）、订单状态机（D-01）、微信支付+支付宝（下单+回调+退款）、订单列表/详情、取消/确认收货、收货地址、订单超时取消 |
| 后台 ERP 基础 | 第 8-9 周 | 数据看板、订单管理（列表/详情/发货）、商品管理、库存管理、运费模板（D-11）、系统设置 |
| 验收与上线 | 第 10 周 | 端到端验证、性能优化、Docker 部署、备份演练 |

**1a 期不包含**：售后、会员管理、低代码搭建器、消息通知、评价

#### D8.1.2 1b 期：完善与扩展（5 周）

目标：补齐商家运营能力，从"能交易"升级到"好运营"。

| 阶段 | 周次 | 交付内容 |
|---|---|---|
| 售后与会员 | 第 1-2 周 | 售后状态机（D-01）、售后管理、退款执行、会员列表/详情、RBAC 完整版（D-04） |
| 消息通知 | 第 3 周 | 通知中心（D-09）、站内信、短信/邮件通知、模板管理 |
| 商品评价 | 第 3 周 | 评价系统（D-10）、评价审核、评价展示 |
| 商城低代码 | 第 4-5 周 | 三栏搭建器、5 个核心组件、属性面板（内容+样式）、撤销重做（D3.3）、保存/自动保存、预览、页面管理、Schema 版本管理（D3.1） |
| 验证 | 第 5 周 | 端到端验证、性能优化、CI 完善 |

**1b 期 5 个核心低代码组件**：搜索框、轮播图、商品网格、图片广告、辅助空白（其余 5 个二期补齐）

### D8.2 二期范围调整

二期在 v1.1 基础上新增：

- 商城低代码扩展至 10 个组件（补齐公告栏、富文本、商品横滑、优惠券占位、分类导航）
- 优惠券完整实现（满减券/折扣券/无门槛券）
- 操作日志查询页（D6.1 缺口 4）
- 数据权限（二期实现，基于 D1.4.5 预留）
- 官网低代码（原 v1.1 二期范围不变）

### D8.3 三期范围调整

三期在 v1.1 基础上调整：

- **3D 作为可选插件**（D-15）：独立包，不强制
- 多租户 SaaS：明确独立部署优先，共享 DB 多租户为可选项（D-17）
- 营销工具：优惠券已二期，三期做拼团/秒杀/分销
- 发票管理：对接第三方电子发票 SaaS（D-22）
- AI 商品文案生成
- 智能补货建议（基于 D6.4.3）
- 物流轨迹实时查询
- AI 推荐系统（基于 D6.7）

### D8.4 优先级落地清单

| 优先级 | 落地阶段 | 决策 |
|---|---|---|
| 🔴 P0 | 1a 期 | D-01 状态机拆分、D-02 金额单位、D-03 购物车、D-04 RBAC、D-05 物流编码、D-08 错误码、D-11 运费模板 |
| 🔴 P0 | 1b 期 | D-06 Schema 版本、D-07 Schema 缓存、D-09 通知中心、D-10 评价系统 |
| 🟡 P1 | 1a/1b 期 | D-12 H5 多级缓存、D-13 ISR 事件、D-14 双构建兼容、D-19 支付前置、D-20 文件上传、D-27 蓝绿部署、D-28 限流、D-29 主题统一 |
| 🟡 P1 | 二期 | D-15 3D 隔离、D-16 分阶段（已完成 1a/1b）、D-17 多租户、D-18 表单加密 |
| 🟢 P2 | 二期 | D-21 i18n、D-23 a11y、D-24 CI 门禁、D-25 读写分离、D-26 Source Map、D-30 A/B 测试 |
| 🟢 P2 | 三期 | D-22 发票对接 |

### D8.5 修订后的排期总览

| 期次 | 周期 | 范围 |
|---|---|---|
| 1a 期 | 10 周 | 核心交易闭环（认证/商品/库存/订单/支付/后台基础） |
| 1b 期 | 5 周 | 售后/会员/通知/评价/低代码 5 组件 |
| 二期 | 6-8 周 | 官网低代码 + 商城低代码扩展至 10 + 优惠券 + 数据权限 |
| 三期 | 4-6 周 | 3D 插件 + 多租户 + 营销 + 发票 + AI |

---

# 附录 E：工程约束与闭环补强（v1.3 增补）

> 以下为 v1.3 评审后增补内容，补齐 v1.2 的未闭环设计与工程约束。若附录 E 与附录 D 冲突，以附录 E 为准。

---

## E0. 闭环性补强清单

对照 v1.2 的 29 项未闭环设计点，逐一在 E1-E6 章节给出补强方案。索引表：

| 未闭环点（见 1.1-1.8） | 补强章节 | 决策编号 |
|---|---|---|
| 1 库存三层模型 DDL | E3.1 | E-01 |
| 2 SPU/SKU 规格表 | E3.2 | E-02 |
| 3 order_items 快照表 | E3.3 | E-03 |
| 4 users/addresses/favorites | E3.4 | E-07 |
| 5 payments/refunds | E3.5 | E-04 |
| 6 pages 表 | E3.6 | E-05 |
| 7 operation_logs | E3.7 | E-06 |
| 8 订单状态机与库存联动 | E3.8 | E-08 |
| 9 OpenAPI 文件清单 | E7.1 | E-09 |
| 10 核心端点契约 | E7.1 | E-09 |
| 11 鉴权 Header 规约 | E7.2 | E-10 |
| 12 文件上传签名接口 | E7.3 | E-11 |
| 13 低代码组件 Schema 示例 | E8 | E-12 |
| 14 组件 props/样式字段 | E8.11 | E-13 |
| 15 组件 ID 一致性 | E8.12 | E-13 |
| 16 SSE 鉴权重连 | E9 | E-14 |
| 17 Outbox worker | E10 | E-15 |
| 18 CSRF/XSS/JWT/bcrypt | E11 | E-16 |
| 19 1a 期验收清单 | E12 | E-31 |
| 20 支付下单回调时序 | E13 | E-17 |
| 21 订单超时与回调竞态 | E14 | E-18 |
| 22 库存原子扣减 SQL | E3.1 | E-01 |
| 23 结构化日志格式 | E15 | E-19 |
| 24 Sentry 初始化 | E16 | E-20 |
| 25-29 其他 | E5/E6 | E-25~E-30 |

---

## E1. 代码约束（E-21）

### E1.1 命名约束

| 类别 | 规约 | 示例 |
|---|---|---|
| 目录 | 各端固定目录结构（见 E1.2） | `src/api/` |
| 组件文件 | PascalCase | `ProductCard.tsx` |
| 组件测试 | 同名 + `.test.tsx` | `ProductCard.test.tsx` |
| 组件 Story | 同名 + `.stories.tsx` | `ProductCard.stories.tsx` |
| 函数/hook | camelCase | `useProductList`、`formatPrice` |
| 常量 | UPPER_SNAKE | `MAX_CART_ITEMS` |
| 类型/接口 | PascalCase | `Product`、`OrderItem` |
| 后端 DTO | PascalCase + 后缀 | `ProductCreate`/`ProductUpdate`/`ProductResponse` |
| DB 表名 | snake_case 复数 | `orders`、`order_items` |
| DB 字段 | snake_case | `created_at` |
| API 路径 | kebab-case 复数 | `/api/v1/order-items/{id}` |
| CSS 类 | kebab-case + BEM | `product-card__title--active` |
| 环境变量 | UPPER_SNAKE | `NEXT_PUBLIC_API_BASE` |
| 枚举值 | UPPER_SNAKE | `PENDING_PAYMENT` |
| Commit scope | 模块名 | `feat(order):`、`fix(cart):` |

### E1.2 后端代码约束

#### E1.2.1 目录结构

```
backend/app/
├── api/                  # 路由层（HTTP 入口）
│   ├── v1/
│   │   ├── auth.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── ...
│   └── deps.py           # 公共依赖
├── core/                 # 基础设施
│   ├── config.py
│   ├── db.py
│   ├── redis.py
│   ├── security.py
│   ├── logging.py
│   └── rate_limiter.py
├── models/               # ORM 模型
├── schemas/              # Pydantic 模型
├── services/             # 业务逻辑层
├── repositories/         # 数据访问层
├── tasks/                # Celery 任务
├── enums.py
├── errors.py             # ApiError + 错误码
└── main.py
```

#### E1.2.2 分层约束

- 严格分层：`api → services → repositories → models`
- 禁止跨层调用（api 不能直接调 repositories）
- 禁止 ORM 模型直接返回 API 响应（必须经 Pydantic schema）
- Pydantic schema 分 `XxxCreate`/`XxxUpdate`/`XxxQuery`/`XxxResponse`

#### E1.2.3 异步约束

- 全异步：`async def` + `asyncpg` + `aioredis`
- 禁止同步 IO（`requests`、`time.sleep`）
- HTTP 客户端用 `httpx.AsyncClient`
- 长任务用 Celery，不阻塞请求线程

#### E1.2.4 事务约束

- 写操作必须 `async with db.transaction():` 包裹
- 跨服务操作必须事务化（如订单创建+库存扣减）
- 事件发布用 Outbox 模式，避免 DB 写成功事件丢失

#### E1.2.5 数据规约

| 类型 | 规约 |
|---|---|
| 金额 | DB Integer 分，Python Decimal 元，Pydantic 输出 int 分 |
| 时间 | DB `TIMESTAMPTZ` 存 UTC，API ISO8601 带时区 |
| 空值 | 对象 null，数组 []，字符串 "" |
| 枚举 | DB 存字符串值，Python `StrEnum` |
| 主键 | `BIGSERIAL`（自增 bigint） |
| 软删除 | `deleted_at TIMESTAMPTZ`，查询自动过滤 |

#### E1.2.6 异常与日志

```python
# backend/app/errors.py
class ApiError(Exception):
    def __init__(self, code: int, message: str, i18n_key: str = '', field: str = '', details: dict = None):
        self.code = code
        self.message = message
        self.i18n_key = i18n_key
        self.field = field
        self.details = details or {}
```

禁止 `except: pass`，异常必须记录或向上抛。

日志格式（E-19）：

```python
# backend/app/core/logging.py
import structlog
log = structlog.get_logger()

log.info('order_created',
    request_id=request_id,
    user_id=user_id,
    order_id=order.id,
    amount_cents=order.total_amount)
```

结构化字段必填：`request_id`、`timestamp`、`level`、`event`、`user_id`（如有）。

### E1.3 前端代码约束

#### E1.3.1 目录结构（H5 端示例）

```
packages/h5-app/src/
├── api/                  # API 调用封装
│   ├── product.ts
│   ├── order.ts
│   └── client.ts         # axios 实例 + 拦截器
├── components/           # 业务组件
│   ├── ProductCard.tsx
│   └── ...
├── hooks/                # 自定义 hooks
│   ├── useProductList.ts
│   └── useCart.ts
├── layouts/              # 布局
├── pages/                # 路由页面
├── routes/               # 路由配置
├── store/                # Zustand store
├── styles/               # 全局样式
├── types/                # 业务类型
└── utils/                # 工具函数
```

#### E1.3.2 组件约束

- 函数组件 + Hooks，禁止 class 组件
- Props 必有 `interface XxxProps`，禁止 `any`
- 服务端状态 React Query，客户端状态 Zustand，禁止 Context 滥用
- 样式：Tailwind 静态类 + CSS 变量动态值，禁止动态拼接 class
- 金额一律 `number`（分），展示前 `formatPrice()`
- API 调用统一走 `src/api/*` + React Query，禁止组件内裸 axios
- 所有展示文本走 i18n key，禁止硬编码中文
- 错误处理：拦截器统一处理 ApiError，组件层显示 toast
- 路由 React Router v6，配置集中 `routes/`
- 大组件 `React.lazy` + Suspense
- 语义化 HTML，禁用 `<div onClick>` 模拟交互

#### E1.3.3 性能约束

- `React.memo` 防止 props 未变化重渲染
- `useMemo`/`useCallback` 缓存计算/函数引用
- 列表 > 50 项用虚拟滚动（react-window）
- 图片懒加载 + 固定宽高比占位防 CLS
- 首屏只加载 above-fold 组件

### E1.4 提交与分支约束

| 类别 | 规约 |
|---|---|
| 分支 | `main` + `feat/{scope}-{slug}` + `fix/{slug}` |
| Commit message | Conventional Commits：`feat(order): add cancel logic` |
| PR 标题 | `[{scope}] {description}` |
| PR 模板 | 含变更说明/验证命令/截图/影响范围 |
| 合并 | Squash merge，主分支保留线性历史 |
| Code Review | 至少 1 人 review，支付/迁移/架构变更需 2 人 |
| 提交粒度 | 一个模块/一次验证通过即 commit |

### E1.5 依赖约束

- 不引入未声明的新依赖；确需引入先在 PR 说明理由
- 前端用 pnpm workspace，后端用 uv/pip
- 锁文件 `pnpm-lock.yaml`/`uv.lock` 提交到 git
- 禁止引入重型依赖（如 three.js 进 shared-components，应放 3d-components）

---

## E2. 前端组件化与设计系统（E-22, E-23）

### E2.1 L0-L4 五层组件分层

```
┌──────────────────────────────────────────────────────┐
│ L4 业务页面（pages）                                   │
│   H5: ProductListPage / CartPage                       │
│   Admin: OrderListPage / ProductEditPage               │
├──────────────────────────────────────────────────────┤
│ L3 业务组合组件（features）                             │
│   H5: ProductCard + AddToCartButton                    │
│   Admin: OrderTable + StatusFilter                     │
├──────────────────────────────────────────────────────┤
│ L2 低代码组件（lowcode）                                │
│   shared-components: SchemaRenderer / ProductGrid      │
│   接收 props/style，可被搭建器配置                      │
├──────────────────────────────────────────────────────┤
│ L1 基础原子组件（primitives）                          │
│   shared-components: Button / Input / Modal / Spinner │
│   基于 antd-mobile (H5) / antd (Admin) 二次封装        │
├──────────────────────────────────────────────────────┤
│ L0 Design Tokens                                       │
│   shared-tokens: CSS 变量 / Tailwind 配置 / 主题      │
└──────────────────────────────────────────────────────┘
```

### E2.2 组件设计规约

| 规约 | 说明 |
|---|---|
| 单一职责 | 一组件只做一事，> 300 行必拆 |
| Props 单向 | 数据下流，事件上报 |
| 受控/非受控 | 表单组件必支持受控，提供 value + onChange |
| 可组合 | children 优于具体 props |
| 可访问性 | 语义化 HTML + ARIA |
| 可测试 | 纯函数 + 易 mock |
| 性能 | memo + useMemo + useCallback |
| 类型完整 | Props 必有 interface，禁 any |
| i18n | 文本走 i18n key |
| 样式隔离 | CSS 变量 + Tailwind，禁全局选择器 |

### E2.3 低代码组件额外规约

| 规约 | 说明 |
|---|---|
| Schema 驱动 | 所有配置项可序列化为 JSON |
| 默认值完整 | 每字段有默认值 |
| 预览态=运行态 | 画布预览与 H5 渲染用同组件，仅外层加选中态包装 |
| 样式四层继承 | 全局 Token → 页面级 → 容器级 → 元素级 |
| 不引用业务 store | 低代码组件不直接调 API，数据通过 props 注入 |
| 版本字段 | 必含 `version`，配合 D3.1 迁移机制 |

### E2.4 Storybook 集成（E-23）

```typescript
// packages/shared-components/src/Button/Button.stories.tsx
import type { Meta, StoryObj } from '@storybook/react';
import { Button } from './Button';

const meta: Meta<typeof Button> = {
  title: 'Primitives/Button',
  component: Button,
  tags: ['autodocs'],
  argTypes: {
    variant: { control: 'select', options: ['primary', 'secondary', 'danger'] },
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
  },
};
export default meta;

type Story = StoryObj<typeof Button>;

export const Primary: Story = {
  args: { variant: 'primary', children: '提交' },
};

export const Loading: Story = {
  args: { variant: 'primary', loading: true, children: '提交' },
};
```

低代码 10 个商城组件全部写 Story，商家在搭建器属性面板切换预览时复用 Storybook 的 args 控制。

---

## E3. 完整数据模型补遗（E-01~E-08）

### E3.1 库存三层模型（E-01）

#### E3.1.1 skus 表完整结构

```sql
CREATE TABLE skus (
    id              BIGSERIAL PRIMARY KEY,
    product_id      BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_code         VARCHAR(50) NOT NULL UNIQUE,        -- SKU 编码
    spec_values     JSONB NOT NULL DEFAULT '{}',          -- {"颜色":"红","尺寸":"M"}
    spec_hash       VARCHAR(64) NOT NULL,                  -- 规格值排序后哈希，防重复
    price_cents     INTEGER NOT NULL,                      -- 销售价（分）
    cost_cents      INTEGER NOT NULL DEFAULT 0,            -- 成本价（分）
    -- 三层库存
    physical_stock  INTEGER NOT NULL DEFAULT 0,            -- 实际库存（入库累计）
    locked_stock    INTEGER NOT NULL DEFAULT 0,            -- 锁定库存（已下单未发货）
    -- available_stock = physical_stock - locked_stock（计算字段，查询时算）
    weight_grams    INTEGER,                               -- 重量（克）
    image           VARCHAR(500),                          -- SKU 级图片
    bar_code        VARCHAR(50),                           -- 条形码
    safety_stock    INTEGER NOT NULL DEFAULT 10,            -- 安全库存阈值
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE / DISABLED
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, spec_hash)
);

CREATE INDEX idx_skus_product_id ON skus(product_id);
CREATE INDEX idx_skus_sku_code ON skus(sku_code);
CREATE INDEX idx_skus_status ON skus(status);

-- 可用库存视图（简化查询）
CREATE VIEW v_skus_available AS
SELECT id, product_id, physical_stock, locked_stock,
       (physical_stock - locked_stock) AS available_stock
FROM skus;
```

#### E3.1.2 库存原子操作 SQL

```sql
-- 1. 下单时锁定库存（available >= qty）
UPDATE skus
SET locked_stock = locked_stock + :qty
WHERE id = :sku_id AND (physical_stock - locked_stock) >= :qty;
-- 检查影响行数 = 1，否则抛 STOCK_INSUFFICIENT

-- 2. 发货时扣减锁定库存 + 实际库存
UPDATE skus
SET locked_stock = locked_stock - :qty,
    physical_stock = physical_stock - :qty
WHERE id = :sku_id AND locked_stock >= :qty;

-- 3. 取消订单回滚锁定库存
UPDATE skus
SET locked_stock = locked_stock - :qty
WHERE id = :sku_id AND locked_stock >= :qty;

-- 4. 售后退款回滚实际库存
UPDATE skus
SET physical_stock = physical_stock + :qty
WHERE id = :sku_id;
```

#### E3.1.3 stock_logs 表

```sql
CREATE TABLE stock_logs (
    id              BIGSERIAL PRIMARY KEY,
    sku_id          BIGINT NOT NULL REFERENCES skus(id),
    source_type     VARCHAR(20) NOT NULL,         -- ORDER_LOCK / ORDER_SHIP / ORDER_CANCEL / AFTER_SALE / PURCHASE / MANUAL
    source_id       BIGINT,                         -- 关联订单/售后/采购单 ID
    change_type     VARCHAR(20) NOT NULL,           -- LOCK / SHIP / UNLOCK / ROLLBACK / INBOUND / ADJUST
    change_qty      INTEGER NOT NULL,                -- 变动数量（正数入库，负数出库）
    physical_before INTEGER NOT NULL,
    physical_after  INTEGER NOT NULL,
    locked_before   INTEGER NOT NULL,
    locked_after    INTEGER NOT NULL,
    operator_id     BIGINT,                          -- 操作人（管理员）
    reason          VARCHAR(200),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stock_logs_sku_id ON stock_logs(sku_id);
CREATE INDEX idx_stock_logs_created_at ON stock_logs(created_at);
CREATE INDEX idx_stock_logs_source ON stock_logs(source_type, source_id);
```

### E3.2 SPU/SKU 规格表（E-02）

```sql
-- 商品分类
CREATE TABLE categories (
    id          BIGSERIAL PRIMARY KEY,
    parent_id   BIGINT REFERENCES categories(id),
    name        VARCHAR(100) NOT NULL,
    icon        VARCHAR(500),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categories_parent_id ON categories(parent_id);

-- 商品 SPU
CREATE TABLE products (
    id              BIGSERIAL PRIMARY KEY,
    category_id     BIGINT REFERENCES categories(id),
    name            VARCHAR(200) NOT NULL,
    subtitle        VARCHAR(200),                    -- 副标题
    brand           VARCHAR(100),
    main_images     JSONB NOT NULL DEFAULT '[]',     -- 主图列表 [{url, is_main, sort_order}]
    detail_images   JSONB NOT NULL DEFAULT '[]',     -- 详情图列表
    detail_html     TEXT,                              -- 详情富文本
    -- SEO 预留
    seo_title       VARCHAR(200),
    seo_description VARCHAR(500),
    seo_keywords    VARCHAR(200),
    -- 状态
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- DRAFT / ON_SHELF / OFF_SHELF
    sort_order      INTEGER NOT NULL DEFAULT 0,
    sales_count     INTEGER NOT NULL DEFAULT 0,       -- 销量冗余字段
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ                       -- 软删除
);

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_status ON products(status) WHERE deleted_at IS NULL;
CREATE INDEX idx_products_name ON products USING GIN(to_tsvector('simple', name));

-- 规格定义
CREATE TABLE product_specs (
    id          BIGSERIAL PRIMARY KEY,
    product_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name        VARCHAR(50) NOT NULL,           -- 规格名，如"颜色""尺寸"
    sort_order  INTEGER NOT NULL DEFAULT 0,
    UNIQUE(product_id, name)
);

-- 规格值
CREATE TABLE product_spec_values (
    id          BIGSERIAL PRIMARY KEY,
    spec_id     BIGINT NOT NULL REFERENCES product_specs(id) ON DELETE CASCADE,
    value       VARCHAR(100) NOT NULL,          -- 规格值，如"红""M"
    sort_order  INTEGER NOT NULL DEFAULT 0,
    UNIQUE(spec_id, value)
);

CREATE INDEX idx_product_spec_values_spec_id ON product_spec_values(spec_id);
```

### E3.3 order_items 快照表（E-03）

```sql
CREATE TABLE order_items (
    id              BIGSERIAL PRIMARY KEY,
    order_id        BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    sku_id          BIGINT NOT NULL REFERENCES skus(id),
    -- 快照字段（下单时的价格/规格，不依赖 SKU 实时数据）
    product_id      BIGINT NOT NULL,
    product_name    VARCHAR(200) NOT NULL,       -- 商品名快照
    sku_code        VARCHAR(50) NOT NULL,          -- SKU 编码快照
    spec_values     JSONB NOT NULL,                -- 规格快照 {"颜色":"红","尺寸":"M"}
    product_image   VARCHAR(500),                  -- 商品主图快照
    price_cents     INTEGER NOT NULL,               -- 单价快照（分）
    quantity        INTEGER NOT NULL,
    -- 优惠分摊（一期 0）
    discount_amount INTEGER NOT NULL DEFAULT 0,
    total_amount    INTEGER NOT NULL,               -- 小计 = price * qty - discount
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_sku_id ON order_items(sku_id);
```

### E3.4 users/addresses/favorites（E-07）

```sql
CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    phone           VARCHAR(20) NOT NULL UNIQUE,
    password_hash   VARCHAR(255),                  -- 密码登录（可选）
    nickname        VARCHAR(50),
    avatar          VARCHAR(500),
    gender          VARCHAR(10),                    -- MALE / FEMALE / UNKNOWN
    birthday        DATE,
    status          VARCHAR(20) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE / DISABLED
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE addresses (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    receiver_name   VARCHAR(50) NOT NULL,
    phone           VARCHAR(20) NOT NULL,
    province_code   VARCHAR(20) NOT NULL,
    city_code       VARCHAR(20) NOT NULL,
    district_code   VARCHAR(20) NOT NULL,
    detail          VARCHAR(500) NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_addresses_user_id ON addresses(user_id);

CREATE TABLE favorites (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id  BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, product_id)
);

CREATE INDEX idx_favorites_user_id ON favorites(user_id);
```

### E3.5 payments/refunds（E-04）

```sql
CREATE TABLE payments (
    id              BIGSERIAL PRIMARY KEY,
    payment_no      VARCHAR(32) NOT NULL UNIQUE,   -- 支付单号
    order_id        BIGINT NOT NULL REFERENCES orders(id),
    user_id         BIGINT NOT NULL REFERENCES users(id),
    channel         VARCHAR(20) NOT NULL,           -- WECHAT / ALIPAY
    amount_cents    INTEGER NOT NULL,                -- 支付金额（分）
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING / SUCCESS / FAILED / REFUNDED
    transaction_id  VARCHAR(100),                   -- 第三方交易号
    paid_at         TIMESTAMPTZ,
    callback_raw    TEXT,                            -- 回调原文（用于审计）
    callback_at     TIMESTAMPTZ,
    fail_reason     VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE UNIQUE INDEX idx_payments_callback_idempotent ON payments(transaction_id) WHERE transaction_id IS NOT NULL;

CREATE TABLE refunds (
    id              BIGSERIAL PRIMARY KEY,
    refund_no      VARCHAR(32) NOT NULL UNIQUE,
    payment_id      BIGINT NOT NULL REFERENCES payments(id),
    after_sale_id  BIGINT REFERENCES after_sales(id),
    amount_cents    INTEGER NOT NULL,
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING', -- PENDING / SUCCESS / FAILED
    transaction_id  VARCHAR(100),
    refund_reason   VARCHAR(500),
    refunded_at     TIMESTAMPTZ,
    fail_reason     VARCHAR(500),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_refunds_payment_id ON refunds(payment_id);
CREATE INDEX idx_refunds_after_sale_id ON refunds(after_sale_id);
```

### E3.6 pages 表（低代码核心表，E-05）

```sql
CREATE TABLE pages (
    id              BIGSERIAL PRIMARY KEY,
    page_type       VARCHAR(20) NOT NULL,           -- H5 / SITE
    name            VARCHAR(100) NOT NULL,
    slug            VARCHAR(100) NOT NULL,          -- 路由路径（官网）/ 标识（H5）
    schema          JSONB NOT NULL DEFAULT '{}',     -- PageSchema（D3.1）
    schema_version  INTEGER NOT NULL DEFAULT 1,      -- 页面 Schema 版本
    -- SEO 配置（官网页）
    seo_title       VARCHAR(200),
    seo_description VARCHAR(500),
    seo_keywords    VARCHAR(200),
    og_image        VARCHAR(500),
    canonical_url   VARCHAR(500),
    noindex         BOOLEAN NOT NULL DEFAULT FALSE,
    nofollow        BOOLEAN NOT NULL DEFAULT FALSE,
    json_ld         JSONB,                            -- 结构化数据
    -- 状态
    is_home         BOOLEAN NOT NULL DEFAULT FALSE,  -- 是否首页
    status          VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- DRAFT / PUBLISHED
    published_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE(page_type, slug) WHERE deleted_at IS NULL
);

CREATE INDEX idx_pages_type_status ON pages(page_type, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_pages_is_home ON pages(page_type) WHERE is_home = TRUE AND deleted_at IS NULL;
```

### E3.7 operation_logs（E-06）

```sql
CREATE TABLE operation_logs (
    id              BIGSERIAL PRIMARY KEY,
    admin_id        BIGINT REFERENCES admins(id),
    resource_type   VARCHAR(50) NOT NULL,           -- ORDER / PRODUCT / SKU / ...
    resource_id    BIGINT,
    action          VARCHAR(50) NOT NULL,            -- CREATE / UPDATE / DELETE / EXPORT
    before_data    JSONB,                             -- 修改前快照
    after_data     JSONB,                             -- 修改后快照
    ip             INET,
    user_agent     TEXT,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_operation_logs_admin_id ON operation_logs(admin_id);
CREATE INDEX idx_operation_logs_resource ON operation_logs(resource_type, resource_id);
CREATE INDEX idx_operation_logs_created_at ON operation_logs(created_at);
```

### E3.8 订单状态机与库存联动时序图（E-08）

```
用户下单
  ↓
1. 校验 SKU 价格库存（D1.3.6）
  ↓
2. 锁定库存：UPDATE skus SET locked_stock += qty（E3.1.2 步骤 1）
  ↓
3. 写 orders (status=PENDING_PAYMENT) + order_items 快照
  ↓
4. 写 stock_logs (change_type=LOCK)
  ↓
5. 写 Redis ZSET 超时队列：order:expire
  ↓
6. 返回订单 + 支付参数

【分支 A：用户支付】
支付回调
  ↓
1. 验签 + 幂等检查（payments.status）
  ↓
2. 加 Redis 分布式锁：lock:order:{order_id}
  ↓
3. 再次检查 orders.status
   - 若 = CANCELLED → 退款（用户超时后支付）
   - 若 = PENDING_PAYMENT → 继续
  ↓
4. UPDATE orders SET status=PAID（乐观锁）
  ↓
5. UPDATE payments SET status=SUCCESS
  ↓
6. 删 Redis ZSET 超时项
  ↓
7. 发 order.paid 事件 → 通知中心

【分支 B：超时取消】
定时任务（每分钟扫 order:expire ZSET）
  ↓
1. 取到期订单 ID
  ↓
2. 加 Redis 分布式锁：lock:order:{order_id}
  ↓
3. 再次检查 orders.status
   - 若 = PAID → 跳过（用户已支付）
   - 若 = PENDING_PAYMENT → 继续
  ↓
4. UPDATE orders SET status=CANCELLED（乐观锁）
  ↓
5. 回滚锁定库存：UPDATE skus SET locked_stock -= qty（E3.1.2 步骤 3）
  ↓
6. 写 stock_logs (change_type=UNLOCK)
  ↓
7. 删 Redis ZSET 超时项
  ↓
8. 发 order.cancelled 事件 → 通知中心

【分支 C：后台发货】
1. UPDATE orders SET status=SHIPPED（条件：status=PAID）
  ↓
2. 扣减实际库存 + 锁定库存：E3.1.2 步骤 2
  ↓
3. 写 stock_logs (change_type=SHIP)
  ↓
4. 写物流信息
  ↓
5. 发 order.shipped 事件

【分支 D：用户确认收货】
1. UPDATE orders SET status=COMPLETED（条件：status=SHIPPED）
  ↓
2. 发 order.completed 事件

【分支 E：售后退款】
1. after_sales 状态流转到 REFUNDING
  ↓
2. 调支付渠道退款接口
  ↓
3. UPDATE refunds SET status=SUCCESS
  ↓
4. 回滚实际库存：E3.1.2 步骤 4
  ↓
5. 写 stock_logs (change_type=ROLLBACK)
  ↓
6. 更新 orders.refund_status
  ↓
7. 发 after_sale.refunded 事件
```

---

## E4. 代码注释规约（E-24）

### E4.1 注释原则

| 原则 | 说明 |
|---|---|
| 代码自解释优先 | 好命名 + 类型 + 短函数胜过注释 |
| 注释"为什么" | 而不是"是什么" |
| 公共 API 必注释 | 函数/类/接口/类型导出必 JSDoc/TSDoc/docstring |
| 复杂逻辑必注释 | 状态机/算法/兼容 hack 必加注释 |
| TODO 必带 issue | `// TODO(#123): 支持部分退款` |
| 业务规则必注释 | 如"30 分钟超时" `// PRD 4.1.4 订单超时 30 分钟自动取消` |
| 不写废话注释 | `// 设置 name` 给 name 赋值——多余 |

### E4.2 文件头注释模板

```typescript
/**
 * @file ProductCard.tsx
 * @description 商品卡片组件，用于商品列表与搜索结果
 * @see PRD 4.1.2 商品模块
 */
```

```python
# -*- coding: utf-8 -*-
"""
@file order/service.py
@description 订单创建/查询/状态流转服务
@see PRD D1.1 订单状态机
"""
```

### E4.3 函数注释模板

```typescript
/**
 * 创建订单
 *
 * 流程：
 * 1. 从 DB 读取 SKU 最新价格库存
 * 2. 校验价格快照一致性，不一致抛 PRICE_CHANGED
 * 3. 锁定库存（stock-=qty, locked+=qty）
 * 4. 写订单 + order_items 快照
 * 5. 清购物车对应项
 *
 * @param userId - 用户 ID
 * @param items - 订单项输入（含 SKU ID + 数量 + 客户端价格快照）
 * @returns 创建的订单
 * @throws ApiError PRICE_CHANGED / STOCK_INSUFFICIENT
 *
 * @see PRD D1.3.6 下单金额校验
 */
export async function createOrder(userId: number, items: OrderItemInput[]): Promise<Order> {
  // ...
}
```

```python
async def create_order(user_id: int, items: list[OrderItemInput]) -> Order:
    """创建订单

    流程：
    1. 从 DB 读取 SKU 最新价格库存
    2. 校验价格快照一致性，不一致抛 PRICE_CHANGED
    3. 锁定库存（stock-=qty, locked+=qty）
    4. 写订单 + order_items 快照
    5. 清购物车对应项

    :param user_id: 用户 ID
    :param items: 订单项输入（含 SKU ID + 数量 + 客户端价格快照）
    :returns: 创建的订单
    :raises ApiError: PRICE_CHANGED / STOCK_INSUFFICIENT

    @see PRD D1.3.6 下单金额校验
    """
```

### E4.4 注释语言

- 中文项目：注释用中文
- 公共 API 文档（Storybook MDX / OpenAPI description）：中文为主，二期加英文
- 代码标识符（变量/函数/类）：英文

### E4.5 不需要注释的场景

- 类型明确的 TS interface
- 简短函数（< 10 行，命名清晰）
- 测试用例（描述性 `it()` 即注释）

---

## E5. 行业对照补充设计（E-25~E-30）

### E5.1 商品多图主图与 SKU 级图（E-25）

已在 E3.2 `products.main_images` 与 `skus.image` 字段中体现。规约：

- `main_images` 是数组，每项 `{url, is_main, sort_order}`
- 一个商品必有且仅有一张 `is_main=true` 的主图
- `skus.image` 可空，空则用 SPU 主图兜底

### E5.2 购物车跨端 token（E-26）

```typescript
// 游客加购时设置 cookie
document.cookie = 'cart_token=' + uuid + '; max-age=2592000; path=/; SameSite=Lax';

// 登录时把 cart_token 与 user_id 绑定
POST /api/auth/login
{ phone, code, cart_token: 'xxx' }
// 后端：合并 cart:guest:{cart_token} 到 cart:user:{user_id}
```

### E5.3 批量操作与导入导出（E-27）

后台统一 `BatchActionBar` 组件：

```tsx
<BatchActionBar
  selectedIds={selected}
  actions={[
    { label: '批量上架', code: 'product:on_shelf', onClick: () => batchUpdate(selected, { status: 'ON_SHELF' }) },
    { label: '批量下架', code: 'product:off_shelf', onClick: () => batchUpdate(selected, { status: 'OFF_SHELF' }) },
    { label: '批量删除', code: 'product:delete', danger: true, onClick: () => batchDelete(selected) },
    { label: '导出 Excel', code: 'product:export', onClick: () => exportExcel(selected) },
  ]}
/>
```

导出接口返回流式 Excel：

```python
@router.get('/products/export')
@require_permission('product:export')
async def export_products(response: Response, ids: list[int] = Query([])):
    wb = generate_excel(await product_repo.get_by_ids(ids))
    stream = BytesIO()
    wb.save(stream)
    response.headers['Content-Disposition'] = 'attachment; filename=products.xlsx'
    return StreamingResponse(stream, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
```

### E5.4 feature_flags 表（E-28）

```sql
CREATE TABLE feature_flags (
    id          BIGSERIAL PRIMARY KEY,
    key         VARCHAR(100) NOT NULL UNIQUE,      -- 'coupon.enabled', 'review.enabled'
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    description VARCHAR(200),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 一期预置
INSERT INTO feature_flags (key, enabled, description) VALUES
('coupon.enabled', FALSE, '优惠券功能（二期）'),
('review.enabled', FALSE, '商品评价（1b 期）'),
('site_builder.enabled', FALSE, '官网低代码（二期）'),
('3d_plugin.enabled', FALSE, '3D 插件（三期）');
```

```python
# backend/app/core/feature_flags.py
async def is_feature_enabled(key: str) -> bool:
    cached = await redis.get(f'feature:{key}')
    if cached is not None:
        return cached == '1'
    flag = await flag_repo.get(key)
    await redis.set(f'feature:{key}', '1' if flag and flag.enabled else '0', ex=300)
    return flag and flag.enabled

# 使用
if await is_feature_enabled('review.enabled'):
    # 渲染评价区
```

### E5.5 Turbo Monorepo 配置（E-29）

```jsonc
// turbo.json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**", ".next/**"]
    },
    "test": {
      "dependsOn": ["build"],
      "outputs": ["coverage/**"]
    },
    "lint": {},
    "dev": {
      "cache": false,
      "persistent": true
    }
  }
}
```

### E5.6 SQLAlchemy 连接池配置（E-30）

```python
# backend/app/core/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,           # 连接池大小
    max_overflow=20,        # 最大溢出
    pool_pre_ping=True,     # 连接前检查
    pool_recycle=3600,      # 1 小时回收
    echo=False,             # 生产关闭 SQL 日志
)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)
```

---

## E6. SSE 鉴权与断线重连（E-14）

### E6.1 SSE 鉴权

EventSource 不支持自定义 Header，改用 query token：

```typescript
// 前端
const token = getToken();
const evtSource = new EventSource(`/api/sse/page-updates?token=${token}`);
```

```python
# 后端
@router.get('/sse/page-updates')
async def sse_endpoint(token: str = Query(...)):
    user = await verify_token(token)  # 鉴权失败抛 401
    async def event_generator():
        async for event in sse_bus.subscribe(user.id):
            yield f'event: {event.type}\ndata: {json.dumps(event.data)}\n\n'
    return StreamingResponse(event_generator(), media_type='text/event-stream')
```

### E6.2 断线重连

```typescript
class ReconnectableEventSource {
  private url: string;
  private es: EventSource | null = null;
  private retryCount = 0;
  private maxRetries = 5;

  constructor(url: string) {
    this.url = url;
    this.connect();
  }

  private connect() {
    this.es = new EventSource(this.url);
    this.es.addEventListener('open', () => { this.retryCount = 0; });
    this.es.addEventListener('error', () => {
      this.es?.close();
      if (this.retryCount < this.maxRetries) {
        const delay = Math.min(1000 * 2 ** this.retryCount, 30000); // 指数退避，最大 30s
        setTimeout(() => this.connect(), delay);
        this.retryCount++;
      }
    });
  }

  addEventListener(type: string, cb: (e: MessageEvent) => void) {
    this.es?.addEventListener(type, cb as any);
  }
}
```

---

## E7. 接口契约补强（E-09~E-11）

### E7.1 OpenAPI 文件清单与核心端点（E-09）

```
docs/api-contracts/v1/
├── auth.yaml             # 认证：登录/刷新/退出
├── user.yaml             # 用户：个人信息/地址/收藏
├── product.yaml          # 商品：分类/列表/详情/搜索
├── cart.yaml             # 购物车：增删改查/合并
├── order.yaml            # 订单：创建/列表/详情/取消/确认
├── payment.yaml          # 支付：下单/回调/退款
├── after-sale.yaml       # 售后：申请/审核/退款
├── review.yaml           # 评价：提交/列表/详情
├── notification.yaml     # 通知：列表/已读
├── page.yaml             # 低代码：页面/Schema
├── freight.yaml          # 运费：模板/计算
├── upload.yaml           # 上传：签名
├── settings.yaml         # 设置：主题/物流公司/feature_flags
└── admin/*.yaml          # 后台接口：商品/订单/库存/会员/...
```

核心端点清单：

| 模块 | 方法 | 路径 | 说明 |
|---|---|---|---|
| 认证 | POST | /api/v1/auth/sms-code | 发送验证码 |
| 认证 | POST | /api/v1/auth/login | 登录 |
| 认证 | POST | /api/v1/auth/refresh | 刷新 Token |
| 认证 | POST | /api/v1/auth/logout | 退出 |
| 商品 | GET | /api/v1/products | 商品列表（分页/筛选/排序） |
| 商品 | GET | /api/v1/products/{id} | 商品详情 |
| 商品 | GET | /api/v1/products/search?q= | 搜索 |
| 商品 | GET | /api/v1/categories | 分类树 |
| 购物车 | GET | /api/v1/cart | 购物车列表 |
| 购物车 | POST | /api/v1/cart/items | 加购 |
| 购物车 | PUT | /api/v1/cart/items/{id} | 改数量 |
| 购物车 | DELETE | /api/v1/cart/items/{id} | 删项 |
| 订单 | POST | /api/v1/orders | 创建订单 |
| 订单 | GET | /api/v1/orders | 订单列表 |
| 订单 | GET | /api/v1/orders/{id} | 订单详情 |
| 订单 | POST | /api/v1/orders/{id}/cancel | 取消订单 |
| 订单 | POST | /api/v1/orders/{id}/confirm | 确认收货 |
| 支付 | POST | /api/v1/payments | 创建支付（返回支付参数） |
| 支付 | POST | /api/v1/payments/wechat/callback | 微信回调 |
| 支付 | POST | /api/v1/payments/alipay/callback | 支付宝回调 |
| 评价 | POST | /api/v1/reviews | 提交评价 |
| 评价 | GET | /api/v1/products/{id}/reviews | 商品评价列表 |
| 通知 | GET | /api/v1/notifications | 站内信 |
| 通知 | PUT | /api/v1/notifications/{id}/read | 标记已读 |
| 页面 | GET | /api/v1/pages/{id}/schema | 页面 Schema |
| 运费 | POST | /api/v1/orders/freight-calc | 计算运费 |
| 上传 | POST | /api/v1/upload/sign | 获取上传签名 |

### E7.2 鉴权 Header 规约（E-10）

```http
Authorization: Bearer <access_token>
```

| Header | 说明 |
|---|---|
| `Authorization` | `Bearer <token>` 格式 |
| `X-Request-Id` | 客户端生成 UUID，便于追踪 |

Token 过期响应：

```json
{
  "code": 20004,
  "message": "Token 已过期",
  "i18nKey": "auth.token_expired",
  "requestId": "req_xxx"
}
```

刷新接口：

```http
POST /api/v1/auth/refresh
Authorization: Bearer <refresh_token>

响应：
{
  "code": 0,
  "data": {
    "accessToken": "...",
    "refreshToken": "...",
    "expiresIn": 7200
  }
}
```

### E7.3 文件上传签名接口（E-11）

```http
POST /api/v1/upload/sign
Content-Type: application/json
Authorization: Bearer <token>

请求体：
{
  "fileName": "product.jpg",
  "fileSize": 1048576,
  "contentType": "image/jpeg"
}

响应：
{
  "code": 0,
  "data": {
    "uploadUrl": "https://bucket.oss.com/path/uuid.jpg",
    "method": "POST",
    "headers": {
      "Authorization": "OSS-signed-string",
      "x-oss-meta-uuid": "..."
    },
    "fileUrl": "https://cdn.liteshop.com/path/uuid.jpg",
    "thumbnailUrl": "https://cdn.liteshop.com/path/uuid.jpg?x-oss-process=image/resize,w_300/format,webp",
    "expiresIn": 900
  }
}
```

---

## E8. 低代码组件完整 Schema 示例（E-12, E-13）

### E8.1 商品网格组件

```json
{
  "id": "comp_001",
  "type": "product-grid",
  "version": 1,
  "props": {
    "productSource": {
      "type": "category",
      "categoryId": 5,
      "sort": "sales"
    },
    "columns": 2,
    "displayCount": 10,
    "showPrice": true,
    "showSales": true,
    "cardStyle": "standard"
  },
  "style": {
    "backgroundColor": "transparent",
    "padding": { "top": 16, "right": 16, "bottom": 16, "left": 16 },
    "margin": { "top": 0, "bottom": 0 }
  },
  "elementStyle": {
    "cardBorderRadius": 8,
    "cardShadow": "0 2px 8px rgba(0,0,0,0.1)",
    "priceColor": "#ff4d4f",
    "titleColor": "#1a1a1a"
  }
}
```

### E8.2 组件 props 与样式字段类型定义（E-13）

```typescript
// packages/shared-types/src/schema/components.ts

export interface ContainerStyle {
  backgroundColor?: string;
  backgroundImage?: string;
  backgroundSize?: 'cover' | 'contain' | 'auto';
  border?: { width: number; color: string; style: 'solid' | 'dashed' };
  borderRadius?: number;
  padding?: { top: number; right: number; bottom: number; left: number };
  margin?: { top: number; bottom: number; left?: number; right?: number };
  boxShadow?: string;
  opacity?: number;
}

export interface ElementStyle {
  [key: string]: string | number | undefined; // 组件自定义元素样式
}

export interface ComponentAnimation {
  enabled: boolean;
  type: 'fade-up' | 'fade-down' | 'fade-left' | 'fade-right' | 'zoom-in' | 'zoom-out' | 'flip' | 'slide-up' | 'blur-in' | 'none';
  duration: number;
  delay: number;
  distance: number;
  once: boolean;
  ease: string;
}

export interface ComponentSchema {
  id: string;
  type: string;
  version: number;
  props: Record<string, any>;
  style: ContainerStyle;
  elementStyle?: ElementStyle;
  animation?: ComponentAnimation;
}

export interface PageSchema {
  schemaVersion: number;
  pageStyle: ContainerStyle;
  seo?: {
    title?: string;
    description?: string;
    keywords?: string;
  };
  components: ComponentSchema[];
}
```

### E8.3 组件 ID 一致性（E-13 续）

- 画布新建组件时由前端生成 UUID（`comp_${nanoid()}`）
- 保存到 `pages.schema` 时保留 ID
- H5 渲染时直接读 schema 中的 ID 作为 React key
- 复制组件生成新 ID，避免 key 冲突

### E8.4 10 个低代码组件 Schema 清单

| 组件 type | 主要 props 字段 |
|---|---|
| `search-bar` | placeholder, borderRadius, backgroundColor, visible |
| `carousel` | images[{url, link}], height, autoPlay, interval, indicatorStyle |
| `image-ad` | images[{url, link}], borderRadius, gap |
| `category-nav` | source(all/custom), columns, iconSize, textColor |
| `product-grid` | productSource{type,categoryId,sort}, columns, displayCount, showPrice, showSales, cardStyle |
| `product-scroll` | productSource, title, displayCount |
| `coupon` | coupons[{id}], style |
| `notice-bar` | text, scrollSpeed, icon, backgroundColor |
| `rich-text` | content(html), fontSize, color, align, backgroundColor |
| `blank-space` | height, backgroundColor |

---

## E9. Outbox worker 轮询与分布式锁（E-15）

```python
# backend/app/core/outbox_worker.py
import asyncio
from redis.asyncio import Redis

POLL_INTERVAL_SEC = 5  # 每 5 秒扫描一次
LOCK_KEY = 'outbox:worker:lock'
LOCK_TTL_SEC = 60

async def run_outbox_worker():
    r = Redis.from_url(REDIS_URL)

    while True:
        # 抢分布式锁，防止多实例并发
        acquired = await r.set(LOCK_KEY, '1', ex=LOCK_TTL_SEC, nx=True)
        if not acquired:
            await asyncio.sleep(POLL_INTERVAL_SEC)
            continue

        try:
            # 取未发布事件，批量 100
            events = await outbox_repo.fetch_unpublished(limit=100)
            for event in events:
                try:
                    await redis_stream.add(f'{event.event_type.split(".")[0]}:events',
                                            event.payload)
                    await outbox_repo.mark_published(event.id)
                except Exception as e:
                    log.error('outbox_publish_failed', event_id=event.id, error=str(e))
        finally:
            await r.delete(LOCK_KEY)

        await asyncio.sleep(POLL_INTERVAL_SEC)
```

---

## E10. CSRF / XSS / JWT / bcrypt 补强（E-16）

### E10.1 CSRF 防护

- 后台 Cookie 用 `SameSite=Lax`，阻止跨站 POST
- 敏感写操作（提现、改密）额外校验 `Origin` / `Referer` Header
- 二期可加 CSRF Token 双重提交 Cookie

### E10.2 XSS 白名单工具

富文本组件渲染统一走 `DOMPurify`：

```typescript
import DOMPurify from 'dompurify';

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['p', 'br', 'b', 'i', 'strong', 'em', 'img', 'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'div', 'span'],
    ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class', 'style'],
  });
}
```

### E10.3 JWT 算法

- HS256（默认，单店够用）
- 三期多租户可升 RS256（公私钥分离）

```python
# backend/app/core/security.py
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 小时
REFRESH_TOKEN_EXPIRE_DAYS = 7
```

### E10.4 bcrypt cost

```python
BCRYPT_COST = 12  # 平衡安全与性能
```

---

## E11. 支付下单与回调时序图（E-17）

```
【下单】
H5 → POST /api/v1/orders（创建订单，status=PENDING_PAYMENT）
  ↓
H5 → POST /api/v1/payments（channel=WECHAT, orderId=xx）
  ↓
后端 → 调微信下单 API（unifiedorder）→ 返回 prepay_id
  ↓
后端 → 返回 H5 支付参数（appId/timeStamp/nonceStr/package/sign）
  ↓
H5 → 调微信 JSAPI 唤起支付

【支付回调】
微信 → POST /api/v1/payments/wechat/callback
  ↓
1. 验签（用 API key 校验签名）
  ↓
2. 幂等检查：查 payments.status
   - SUCCESS → 直接返回 SUCCESS（已处理）
   - PENDING → 继续
  ↓
3. 加分布式锁 lock:order:{order_id}
  ↓
4. 金额校验：回调金额 == payments.amount_cents
  ↓
5. 查 orders.status
   - CANCELLED → 调退款（用户超时后支付），返回 SUCCESS
   - PENDING_PAYMENT → 继续
  ↓
6. 事务内：
   - UPDATE orders SET status=PAID
   - UPDATE payments SET status=SUCCESS, transaction_id
   - 删 Redis ZSET 超时项
  ↓
7. 发 order.paid 事件
  ↓
8. 返回微信 SUCCESS
```

---

## E12. 订单超时与支付回调竞态（E-18）

核心：**用分布式锁串行化**，避免定时任务与回调并发。

```
场景：用户在第 29:59 支付，第 30:00 定时任务触发取消

定时任务                        支付回调
   │                              │
   ├─ 扫到过期订单                ├─ 收到微信回调
   ├─ 加锁 lock:order:123 ✅     ├─ 加锁 lock:order:123 ❌（等待）
   ├─ 查 status=PENDING_PAYMENT   │
   ├─ UPDATE status=CANCELLED     │
   ├─ 回滚库存                    │
   ├─ 释放锁                      │
   │                              ├─ 拿到锁
   │                              ├─ 查 status=CANCELLED
   │                              ├─ 触发退款（用户超时后支付）
   │                              ├─ 释放锁
```

或反向：回调先拿到锁，定时任务后拿到锁发现已 PAID 直接跳过。

---

## E13. 结构化日志格式（E-19）

```python
# backend/app/core/logging.py
import structlog
import logging

logging.basicConfig(format='%(message)s', level=logging.INFO)
structlog.configure(
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt='iso'),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
)

log = structlog.get_logger()

# 字段规约
# - timestamp: ISO8601
# - level: INFO/WARN/ERROR
# - event: 'order_created' / 'payment_callback' / ...
# - request_id: 请求追踪 ID
# - user_id: 用户 ID（如适用）
# - + 业务字段
```

---

## E14. Sentry 初始化与敏感字段过滤（E-20）

```typescript
// packages/h5-app/src/sentry.ts
import * as Sentry from '@sentry/react';

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  release: __APP_VERSION__,
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,
  beforeSend(event) {
    // 过滤敏感字段
    if (event.request?.headers) {
      delete event.request.headers['Authorization'];
    }
    return event;
  },
});
```

```python
# backend/app/core/sentry.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    release=settings.APP_VERSION,
    environment=settings.ENV,
    integrations=[FastApiIntegration()],
    traces_sample_rate=0.1,
    before_send=lambda event, hint: filter_sensitive(event),
)

def filter_sensitive(event):
    if 'request' in event:
        headers = event['request'].get('headers', {})
        for k in ['authorization', 'cookie', 'x-api-key']:
            headers.pop(k, None)
    return event
```

---

## E15. 1a 期验收清单（E-31）

### E15.1 功能验收

| # | 场景 | 验收点 |
|---|---|---|
| 1 | 用户注册登录 | 手机号+验证码登录成功，JWT 下发 |
| 2 | 商品浏览 | 分类/列表/详情/SKU 选择正常 |
| 3 | 搜索 | 关键词搜索返回相关性排序结果 |
| 4 | 购物车 | 加购/改数量/删除/全选/合计计算 |
| 5 | 下单 | 收货地址/运费计算/订单提交 |
| 6 | 支付 | 微信/支付宝下单+回调+幂等 |
| 7 | 订单管理 | 列表/详情/取消/确认收货 |
| 8 | 订单超时 | 30 分钟未支付自动取消+库存回滚 |
| 9 | 库存扣减 | 10 并发下单 5 件库存，零超卖 |
| 10 | 后台商品管理 | SPU/SKU/分类 CRUD + 上下架 |
| 11 | 后台订单管理 | 列表/详情/发货/取消/改地址/改价 |
| 12 | 后台库存管理 | 实时库存/锁定库存/流水/预警 |
| 13 | 运费模板 | 按地区/重量/件数计费正确 |
| 14 | 系统设置 | 店铺/支付/OSS/短信配置 |
| 15 | RBAC | 不同角色不同菜单/按钮权限 |
| 16 | 操作日志 | 写操作记录+查询页 |

### E15.2 非功能验收

| # | 项 | 验收点 |
|---|---|---|
| 17 | H5 首屏 | < 2s（4G 模拟） |
| 18 | 接口响应 | 普通查询 < 200ms，下单 < 500ms |
| 19 | 构建 | H5/Admin/Backend 全部构建成功 |
| 20 | 类型检查 | tsc --noEmit + mypy 零错误 |
| 21 | 单测覆盖 | 后端 ≥ 80%，前端 ≥ 70% |
| 22 | 部署 | Docker Compose 一键启动 |
| 23 | 备份 | pg_dump + 恢复演练通过 |
| 24 | 健康检查 | /health /ready 返回正确 |
| 25 | 日志 | 结构化日志含 request_id |
| 26 | Sentry | 错误能上报 |
| 27 | 蓝绿 | 部署脚本 + 回滚演练通过 |

### E15.3 代码质量验收

| # | 项 | 验收点 |
|---|---|---|
| 28 | Lint | ESLint + Prettier + ruff 零错误 |
| 29 | 注释 | 公共 API 全部有 TSDoc/docstring |
| 30 | 组件化 | 共享组件有 Storybook |
| 31 | 提交规范 | Conventional Commits 全部符合 |
| 32 | CI 全绿 | lint/test/build/bundle-size/a11y/contract 全通过 |

---

## E16. 前端防抖与后端幂等双层防护（E-32，v1.3 增补）

### E16.1 问题背景

电商系统最容易因"重复请求"出事故的场景：

| 场景 | 触发原因 | 后果 |
|---|---|---|
| 下单 | 用户双击/网络慢重试 | 创建多个相同订单 + 多次扣库存 |
| 支付 | 用户多次点支付按钮 | 多次调起支付，可能多次扣款 |
| 加购 | 快速点 + 按钮 | 数量异常 |
| 发货 | 后台双击发货 | 物流单重复 |
| 改价 | 后台连续改价 | 互相覆盖 |
| 表单提交 | 联系表单双击 | 多次提交 |
| 删除 | 快速点删除 | 报错（已删除） |
| 短信发送 | 连续点"发送验证码" | 短信费用浪费 |

**防护原则：前端防抖是体验优化，后端幂等是安全兜底。两者缺一不可，以后端幂等为最终防线。**

### E16.2 前端防抖方案

#### E16.2.1 通用防抖 Hook

```typescript
// packages/shared-components/src/hooks/useDebounceAction.ts
import { useState, useRef, useCallback } from 'react';

interface UseDebounceActionOptions {
  /** 防抖延迟（ms），默认 500 */
  delay?: number;
  /** 是否在请求期间禁用按钮，默认 true */
  disableDuringRequest?: boolean;
  /** 是否忽略错误后立即解锁，默认 true */
  unlockOnError?: boolean;
}

/**
 * 防抖 Action Hook：用于提交/下单/支付等"不可重复"操作
 *
 * - 同一动作在 delay 内只执行最后一次
 * - 请求期间按钮 disabled
 * - 失败后自动解锁（可重试）
 * - 成功后保持 disabled（由调用方控制导航/跳转）
 */
export function useDebounceAction<T extends (...args: any[]) => Promise<any>>(
  action: T,
  options: UseDebounceActionOptions = {}
) {
  const { delay = 500, disableDuringRequest = true, unlockOnError = true } = options;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const requestIdRef = useRef<string | null>(null);

  const run = useCallback(async (...args: Parameters<T>) => {
    // 请求中直接拒绝（最硬防线）
    if (disableDuringRequest && loading) return;

    // 防抖：清除前一个未触发的请求
    if (timerRef.current) clearTimeout(timerRef.current);

    return new Promise<Awaited<ReturnType<T>>>((resolve, reject) => {
      timerRef.current = setTimeout(async () => {
        // 生成请求 ID（用于后端幂等）
        requestIdRef.current = `req_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
        setLoading(true);
        setError(null);
        try {
          // 把 requestId 注入第一个参数（约定为对象）
          const input = args[0] ?? {};
          const result = await action({
            ...input,
            _requestId: requestIdRef.current,
          });
          resolve(result);
          // 成功后保持 loading（由调用方在导航/关闭弹窗后重置）
        } catch (e) {
          setError(e as Error);
          if (unlockOnError) setLoading(false);
          reject(e);
        }
      }, delay);
    });
  }, [action, delay, disableDuringRequest, loading, unlockOnError]);

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  return { run, loading, error, reset, requestId: requestIdRef.current };
}
```

#### E16.2.2 下单按钮封装

```tsx
// packages/h5-app/src/components/SubmitOrderButton.tsx
import { useDebounceAction } from '@liteshop/shared-components';
import { Button, Toast } from 'antd-mobile';
import { useNavigate } from 'react-router-dom';

export function SubmitOrderButton({ orderData }: { orderData: OrderData }) {
  const navigate = useNavigate();
  const { run, loading } = useDebounceAction(createOrder, { delay: 800 });

  const handleClick = async () => {
    try {
      const order = await run(orderData);
      Toast.show({ content: '下单成功' });
      navigate(`/order/${order.id}`);
    } catch (e) {
      const err = e as ApiError;
      if (err.code === 20302) {
        // ORDER_STATUS_CONFLICT：已有相同订单
        Toast.show({ content: '订单已创建，请勿重复提交' });
      } else {
        Toast.show({ content: err.message });
      }
    }
  };

  return (
    <Button
      type="submit"
      block
      color="primary"
      loading={loading}
      disabled={loading}
      onClick={handleClick}
    >
      {loading ? '提交中...' : '提交订单'}
    </Button>
  );
}
```

#### E16.2.3 支付按钮防抖

支付按钮特殊处理：防止多次调起微信/支付宝 SDK。

```tsx
// packages/h5-app/src/components/PayButton.tsx
import { useState, useRef, useCallback } from 'react';
import { Button, Toast } from 'antd-mobile';

export function PayButton({ orderId, amount }: { orderId: number; amount: number }) {
  const [loading, setLoading] = useState(false);
  const paidRef = useRef(false);  // 单次会话内支付标记

  const handlePay = useCallback(async () => {
    // 会话内幂等：已调起支付则不再触发
    if (paidRef.current || loading) {
      Toast.show({ content: '正在调起支付，请勿重复点击' });
      return;
    }

    setLoading(true);
    try {
      const res = await api.post('/api/v1/payments', {
        orderId,
        channel: 'WECHAT',
        _requestId: `pay_${orderId}_${Date.now()}`,
      });
      paidRef.current = true;

      // 调起微信 JSAPI
      window.WeixinJSBridge.invoke(
        'getBrandWCPayRequest',
        { ...res.data.payParams },
        (r: any) => {
          if (r.err_msg === 'get_brand_wcpay_request:ok') {
            Toast.show({ content: '支付成功' });
            navigate(`/order/${orderId}/result`);
          } else if (r.err_msg === 'get_brand_wcpay_request:cancel') {
            // 用户取消，重置允许再次支付
            paidRef.current = false;
            setLoading(false);
          } else {
            // 失败，允许重试
            paidRef.current = false;
            setLoading(false);
            Toast.show({ content: '支付失败，请重试' });
          }
        }
      );
    } catch (e) {
      paidRef.current = false;
      setLoading(false);
      Toast.show({ content: (e as Error).message });
    }
  }, [orderId, loading, navigate]);

  return (
    <Button
      block
      color="primary"
      loading={loading}
      disabled={loading}
      onClick={handlePay}
    >
      {loading ? '调起支付中...' : `支付 ¥${formatPrice(amount)}`}
    </Button>
  );
}
```

#### E16.2.4 通用禁用规则

**所有"写"操作按钮的硬性规约**（写入 E1.3 组件约束）：

| 按钮类型 | 防抖策略 | disabled 条件 |
|---|---|---|
| 下单/提交订单 | 防抖 800ms + loading | loading 期间 disabled |
| 支付 | 单次会话内幂等 + loading | paidRef 或 loading 期间 disabled |
| 加购 | 防抖 300ms（不影响体验） | loading 期间 disabled |
| 删除 | 防抖 500ms + loading | loading 期间 disabled |
| 表单提交 | 防抖 1000ms + loading | loading 期间 disabled |
| 短信验证码 | 倒计时 60s | 倒计时期间 disabled |
| 后台发货/改价 | 防抖 500ms + loading | loading 期间 disabled |
| 收藏/取消收藏 | 防抖 200ms | loading 期间 disabled |
| 点赞/有用 | 防抖 200ms + 乐观更新 | — |

**禁止**：在 loading 期间允许用户重复点击，即使按钮看起来"未禁用"。所有写按钮必须在 loading 期间 `disabled=true`。

#### E16.2.5 网络重试与幂等结合

React Query 默认失败重试 3 次。必须关闭对写操作的重试，或结合幂等键重试：

```typescript
// packages/h5-app/src/api/client.ts
import { useMutation } from '@tanstack/react-query';

// 写操作：关闭重试，避免后端创建多条
export function useCreateOrder() {
  return useMutation({
    mutationFn: (data: OrderCreateInput) => api.post('/api/v1/orders', data),
    retry: 0,  // 关键：写操作不重试
  });
}

// 读操作：可重试
export function useProductList() {
  return useQuery({
    queryKey: ['products'],
    queryFn: () => api.get('/api/v1/products'),
    retry: 3,
  });
}
```

若确需重试写操作，必须带幂等键，由后端去重：

```typescript
// 幂等重试示例
async function createOrderWithRetry(data: OrderCreateInput, maxRetries = 2) {
  const requestId = `order_${data.userId}_${Date.now()}`;
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await api.post('/api/v1/orders', { ...data, _requestId: requestId });
    } catch (e) {
      if (i === maxRetries) throw e;
      if (e.code === 20302) {
        // ORDER_STATUS_CONFLICT：已被创建，查回原订单
        return await api.get(`/api/v1/orders/by-request-id/${requestId}`);
      }
      await new Promise(r => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

### E16.3 后端幂等方案

前端防抖会被绕过（直接调 API、网络重发），后端必须兜底。

#### E16.3.1 幂等键设计

每个写操作请求带 `_requestId`（前端生成 UUID + 时间戳）。后端用 `(user_id, _requestId, action_type)` 作幂等键，存 Redis 5 分钟。

| 接口 | 幂等键 | TTL | 已存在时行为 |
|---|---|---|---|
| POST /api/v1/orders | `(userId, _requestId)` | 5min | 返回已创建的订单 |
| POST /api/v1/payments | `(orderId, _requestId)` | 5min | 返回已创建的支付单 |
| POST /api/v1/cart/items | `(userId, skuId, _requestId)` | 1min | 忽略，返回成功 |
| POST /api/v1/reviews | `(userId, orderItemId, _requestId)` | 5min | 返回已创建评价 |
| POST /api/v1/form-submissions | `(email, contentHash, _requestId)` | 5min | 返回已提交记录 |
| POST /api/v1/auth/sms-code | `(phone)` | 60s | 返回"已发送" |
| POST /api/v1/after-sales | `(orderId, userId, _requestId)` | 5min | 返回已创建售后单 |

#### E16.3.2 Redis 幂等实现

```python
# backend/app/core/idempotency.py
import json
import redis.asyncio as redis

class IdempotencyService:
    def __init__(self, redis_url: str):
        self.r = redis.from_url(redis_url)

    async def check_and_lock(
        self,
        key: str,
        ttl_sec: int = 300
    ) -> tuple[bool, dict | None]:
        """
        检查幂等键是否已存在。
        :returns: (is_first_request, cached_response_if_exists)
        """
        # 用 SET NX 抢锁，抢到说明是首次请求
        acquired = await self.r.set(key, 'PENDING', ex=ttl_sec, nx=True)
        if acquired:
            return True, None

        # 已存在：可能是正在处理或已完成
        cached = await self.r.get(key)
        if cached == 'PENDING':
            # 前一个请求还在处理，让客户端稍后重试
            raise ApiError(
                code=42901,
                message='请求正在处理，请稍后再试',
                i18n_key='common.request_in_progress'
            )

        # 已完成：返回缓存的响应
        return False, json.loads(cached)

    async def cache_response(self, key: str, response: dict, ttl_sec: int = 300):
        """缓存首次请求的响应"""
        await self.r.set(key, json.dumps(response), ex=ttl_sec)

    async def clear(self, key: str):
        """失败时清除锁，允许重试"""
        await self.r.delete(key)
```

#### E16.3.3 下单接口幂等实现

```python
# backend/app/api/v1/order.py
from app.core.idempotency import idempotency_service

@router.post('/orders', response_model=OrderResponse)
async def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    request: Request
):
    # 1. 幂等检查
    idempotency_key = f'order:create:{current_user.id}:{payload._requestId}'
    is_first, cached = await idempotency_service.check_and_lock(idempotency_key, ttl_sec=300)

    if not is_first:
        # 已有相同请求，返回已创建的订单
        return cached  # 返回 200 + 已存在的订单数据

    try:
        # 2. 执行业务逻辑（D1.3.6 + E3.8）
        order = await order_service.create_order(
            user_id=current_user.id,
            items=payload.items,
            address_id=payload.addressId,
            remark=payload.remark,
        )

        # 3. 缓存响应
        response_data = OrderResponse.model_validate(order).model_dump()
        await idempotency_service.cache_response(idempotency_key, response_data, ttl_sec=300)

        return response_data

    except ApiError as e:
        # 业务异常：清除锁，允许用户修正后重试
        await idempotency_service.clear(idempotency_key)
        raise e
    except Exception as e:
        # 未知异常：清除锁
        await idempotency_service.clear(idempotency_key)
        log.error('order_create_failed', error=str(e), user_id=current_user.id)
        raise ApiError(code=50000, message='服务器错误')
```

#### E16.3.4 DB 唯一索引兜底

即使 Redis 故障，DB 唯一索引仍是最后防线：

```sql
-- 订单创建防重：同一用户 5 分钟内相同购物车快照只能创建一个订单
-- 通过 _requestId 字段做唯一索引
ALTER TABLE orders ADD COLUMN client_request_id VARCHAR(64);
CREATE UNIQUE INDEX idx_orders_client_request
  ON orders(user_id, client_request_id)
  WHERE client_request_id IS NOT NULL;
```

```python
# backend/app/order/service.py
async def create_order(user_id: int, items: list, client_request_id: str | None):
    try:
        order = await order_repo.create(
            user_id=user_id,
            items=items,
            client_request_id=client_request_id,
            ...
        )
    except IntegrityError as e:
        # 唯一索引冲突：说明已创建，查回原订单
        if client_request_id:
            order = await order_repo.get_by_client_request(user_id, client_request_id)
            log.info('order_duplicate_request_returned',
                     user_id=user_id, client_request_id=client_request_id)
            return order
        raise e
    return order
```

#### E16.3.5 支付接口幂等

```python
# backend/app/api/v1/payment.py
@router.post('/payments', response_model=PaymentResponse)
async def create_payment(
    payload: PaymentCreate,
    current_user: User = Depends(get_current_user),
):
    # 1. 幂等：同一订单同一 _requestId 只创建一次支付单
    idempotency_key = f'payment:create:{payload.orderId}:{payload._requestId}'
    is_first, cached = await idempotency_service.check_and_lock(idempotency_key, ttl_sec=300)

    if not is_first:
        return cached  # 返回已创建的支付参数

    try:
        # 2. 查订单
        order = await order_repo.get(payload.orderId)
        if order.user_id != current_user.id:
            raise ApiError(code=40003, message='无权操作此订单')

        # 3. 检查订单状态
        if order.status != 'PENDING_PAYMENT':
            if order.status == 'PAID':
                raise ApiError(code=20501, message='订单已支付')
            raise ApiError(code=20307, message='订单当前状态不可支付')

        # 4. 检查是否已有进行中的支付单
        existing_payment = await payment_repo.find_pending_by_order(payload.orderId)
        if existing_payment:
            # 已有未完成支付，返回原支付参数（微信 prepay_id 2 小时有效）
            return PaymentResponse.model_validate(existing_payment)

        # 5. 调微信下单 API
        payment = await payment_service.create_wechat_payment(order)
        response_data = PaymentResponse.model_validate(payment).model_dump()
        await idempotency_service.cache_response(idempotency_key, response_data, ttl_sec=300)
        return response_data

    except ApiError:
        await idempotency_service.clear(idempotency_key)
        raise
```

### E16.4 各场景完整防护链路

#### E16.4.1 下单场景

```
用户点"提交订单"
  ↓
【前端 L1】按钮立即 disabled + loading
  ↓
【前端 L2】防抖 800ms（useDebounceAction）
  ↓
【前端 L3】生成 _requestId 注入请求体
  ↓
POST /api/v1/orders { _requestId, items, ... }
  ↓
【后端 L1】Redis 幂等检查（SET NX）
  ├─ 首次 → 继续
  └─ 已存在 PENDING → 抛 REQUEST_IN_PROGRESS（429）
  └─ 已完成 → 返回缓存的订单（200）
  ↓
【后端 L2】业务逻辑执行
  ├─ 库存锁定（原子 SQL）
  ├─ 写 orders + order_items（含 client_request_id）
  └─ 失败 → 清 Redis 锁，抛业务错误
  ↓
【后端 L3】DB 唯一索引兜底
  └─ IntegrityError → 查回原订单返回
  ↓
【后端 L4】缓存响应到 Redis
  ↓
返回订单
  ↓
【前端】跳转订单详情
```

#### E16.4.2 支付场景

```
用户点"支付"
  ↓
【前端 L1】按钮 disabled + loading + paidRef
  ↓
【前端 L2】生成 _requestId
  ↓
POST /api/v1/payments { orderId, _requestId }
  ↓
【后端 L1】Redis 幂等检查
  ├─ 首次 → 继续
  ├─ 已完成 → 返回原支付参数（微信 prepay_id 有效）
  └─ PENDING → 429
  ↓
【后端 L2】查订单状态
  ├─ PENDING_PAYMENT → 继续
  ├─ PAID → 抛 ORDER_PAID
  └─ CANCELLED → 抛 ORDER_CANNOT_PAY
  ↓
【后端 L3】查已有支付单
  ├─ 有 PENDING 支付单 → 直接返回（不重复调微信）
  └─ 无 → 调微信 unifiedorder API
  ↓
【后端 L4】写 payments + 缓存响应
  ↓
返回支付参数
  ↓
【前端】调起微信 JSAPI
  ├─ 用户支付成功 → 跳结果页
  ├─ 用户取消 → 重置 paidRef，允许重新支付
  └─ 失败 → 重置 paidRef，允许重试
```

#### E16.4.3 加购场景

加购是"累加"操作，幂等策略不同：用 `(userId, skuId, _requestId)` 作幂等键，**重复请求直接返回成功但不累加**。

```python
@router.post('/cart/items')
async def add_to_cart(payload: CartItemCreate, current_user=Depends(get_current_user)):
    # 幂等：1 分钟内相同 _requestId 不累加
    idempotency_key = f'cart:add:{current_user.id}:{payload.skuId}:{payload._requestId}'
    is_first, cached = await idempotency_service.check_and_lock(idempotency_key, ttl_sec=60)

    if not is_first:
        return cached  # 返回购物车快照

    try:
        cart = await cart_service.add_item(
            user_id=current_user.id,
            sku_id=payload.skuId,
            quantity=payload.quantity,
        )
        response = {'cart': cart}
        await idempotency_service.cache_response(idempotency_key, response, ttl_sec=60)
        return response
    except ApiError:
        await idempotency_service.clear(idempotency_key)
        raise
```

### E16.5 后台写操作防抖

后台发货/改价/取消订单也需防抖：

```python
# 后台订单发货幂等
@router.post('/admin/orders/{order_id}/ship')
@require_permission('order:ship')
async def ship_order(
    order_id: int,
    payload: ShipOrderInput,  # 含 _requestId
    current_admin=Depends(get_current_admin),
):
    idempotency_key = f'admin:order:ship:{order_id}:{payload._requestId}'
    is_first, cached = await idempotency_service.check_and_lock(idempotency_key, ttl_sec=300)

    if not is_first:
        return cached

    try:
        # 状态机校验：只有 PAID 才能发货
        result = await order_service.ship(
            order_id=order_id,
            logistics_company=payload.logisticsCompany,
            tracking_no=payload.trackingNo,
            admin_id=current_admin.id,
        )
        response = OrderResponse.model_validate(result).model_dump()
        await idempotency_service.cache_response(idempotency_key, response, ttl_sec=300)
        return response
    except ApiError:
        await idempotency_service.clear(idempotency_key)
        raise
```

### E16.6 短信验证码限流（防刷 + 防抖）

短信验证码特殊：用户连续点"发送"按钮，既要防抖又要防刷。

```typescript
// 前端：60 秒倒计时
function useSmsCountdown() {
  const [count, setCount] = useState(0);

  const start = useCallback(() => {
    setCount(60);
    const timer = setInterval(() => {
      setCount(c => {
        if (c <= 1) {
          clearInterval(timer);
          return 0;
        }
        return c - 1;
      });
    }, 1000);
  }, []);

  return { count, start, disabled: count > 0 };
}
```

后端配合 D2.6 限流：手机号 1 次/60s + 5 次/天。

### E16.7 测试用例

防抖与幂等的测试必须覆盖：

```typescript
// packages/h5-app/src/components/__tests__/SubmitOrderButton.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { SubmitOrderButton } from '../SubmitOrderButton';

describe('SubmitOrderButton 防抖', () => {
  it('快速点击 5 次只创建 1 个订单', async () => {
    const createOrder = jest.fn().mockResolvedValue({ id: 1 });
    render(<SubmitOrderButton orderData={...} />);

    const button = screen.getByText('提交订单');
    // 模拟用户狂点
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);
    fireEvent.click(button);

    await waitFor(() => {
      expect(createOrder).toHaveBeenCalledTimes(1);
    });
  });

  it('loading 期间按钮 disabled', async () => {
    render(<SubmitOrderButton orderData={...} />);
    const button = screen.getByText('提交订单');
    fireEvent.click(button);
    expect(button).toBeDisabled();
  });
});
```

```python
# backend/tests/test_order_idempotency.py
import pytest

@pytest.mark.asyncio
async def test_create_order_idempotent(client, auth_headers):
    """同一 _requestId 重复请求只创建一个订单"""
    payload = {
        'items': [{'skuId': 1, 'quantity': 1, 'priceCents': 1999}],
        'addressId': 1,
        '_requestId': 'req_test_001',
    }

    # 第一次请求
    resp1 = await client.post('/api/v1/orders', json=payload, headers=auth_headers)
    assert resp1.status_code == 200
    order_id_1 = resp1.json()['data']['id']

    # 第二次相同 _requestId
    resp2 = await client.post('/api/v1/orders', json=payload, headers=auth_headers)
    assert resp2.status_code == 200
    order_id_2 = resp2.json()['data']['id']

    # 应返回同一订单
    assert order_id_1 == order_id_2

    # DB 只应有 1 个订单
    orders = await db.fetch_all('SELECT * FROM orders WHERE client_request_id = $1', ('req_test_001',))
    assert len(orders) == 1

@pytest.mark.asyncio
async def test_create_order_concurrent(client, auth_headers):
    """并发请求只创建一个订单"""
    payload = { ..., '_requestId': 'req_concurrent_001' }

    # 10 个并发请求
    tasks = [client.post('/api/v1/orders', json=payload, headers=auth_headers) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    order_ids = {r.json()['data']['id'] for r in results if r.status_code == 200}
    assert len(order_ids) == 1  # 只创建一个订单

    # 其他应为 429 或返回缓存的订单
    for r in results:
        assert r.status_code in (200, 429)
```

### E16.8 补充到 E1.3 前端约束

在 E1.3.2 组件约束新增一条：

> **写操作按钮必须使用 `useDebounceAction` Hook 或等价防抖**：所有 POST/PUT/DELETE 操作的按钮，必须在 loading 期间 `disabled=true`，并用防抖 Hook 防止快速重复点击。下单/支付按钮的防抖延迟 ≥ 500ms。

### E16.9 补充错误码

在 D2.2 错误码表新增：

| code | i18nKey | 默认 message | HTTP | 模块 |
|---|---|---|---|---|
| 42901 | common.request_in_progress | 请求正在处理，请稍后再试 | 429 | 通用 |
| 42902 | common.duplicate_request | 重复请求，已为您返回原结果 | 200 | 通用 |

### E16.10 监控指标

新增 Prometheus 指标：

```
liteshop_idempotency_hits_total{action="order_create"} 12   # 幂等命中次数
liteshop_idempotency_miss_total{action="order_create"} 234  # 首次请求次数
```

命中率 > 5% 时告警，可能前端防抖失效或用户重复点击严重，需优化前端体验。

---

**文档结束**

> 本文档为 LiteShop 轻店 PRD v1.3，在 v1.2 附录 D 基础上增补附录 E（工程约束与闭环补强）。若附录 E 与附录 D 冲突，以附录 E 为准。后续如有需求变更，应更新版本号并记录变更日志。
