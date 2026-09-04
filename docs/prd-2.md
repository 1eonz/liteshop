
#### D1.1.3 orders 表结构修订

```sql
CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    order_no        VARCHAR(32) NOT NULL UNIQUE,          -- 订单号
    user_id         BIGINT NOT NULL REFERENCES users(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING_PAYMENT',
    refund_status   VARCHAR(20) NOT NULL DEFAULT 'NONE',  -- v1.2 新增
    total_amount    INTEGER NOT NULL,                      -- 订单总金额（分）
    product_amount  INTEGER NOT NULL,                      -- 商品总金额（分）
    freight_amount  INTEGER NOT NULL DEFAULT 0,            -- 运费金额（分）
    discount_amount INTEGER NOT NULL DEFAULT 0,            -- 优惠金额（分）（一期预留）
    paid_amount     INTEGER,                               -- 实付金额（分）
    address_snapshot JSONB NOT NULL,                       -- 收货地址快照
    remark          TEXT,
    paid_at         TIMESTAMPTZ,
    shipped_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    cancel_reason   VARCHAR(200),
    expired_at      TIMESTAMPTZ,                           -- 支付超时时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_expired_at ON orders(expired_at) WHERE status = 'PENDING_PAYMENT';
```

#### D1.1.4 after_sales 表结构

```sql
CREATE TABLE after_sales (
    id              BIGSERIAL PRIMARY KEY,
    after_sale_no   VARCHAR(32) NOT NULL UNIQUE,          -- 售后单号
    order_id        BIGINT NOT NULL REFERENCES orders(id),
    user_id         BIGINT NOT NULL REFERENCES users(id),
    type            VARCHAR(20) NOT NULL,                 -- REFUND_ONLY / REFUND_AND_RETURN / EXCHANGE
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    reason          TEXT NOT NULL,
    refund_amount   INTEGER NOT NULL,                      -- 退款金额（分）
    return_address  JSONB,                                 -- 退货地址（后台填写）
    return_tracking VARCHAR(100),                          -- 退货物流单号
    admin_remark    TEXT,                                  -- 后台备注
    reviewed_at     TIMESTAMPTZ,
    returned_at     TIMESTAMPTZ,
    refunded_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_after_sales_order_id ON after_sales(order_id);
CREATE INDEX idx_after_sales_user_id ON after_sales(user_id);
CREATE INDEX idx_after_sales_status ON after_sales(status);
```

#### D1.1.5 after_sale_items 关联表

```sql
CREATE TABLE after_sale_items (
    id              BIGSERIAL PRIMARY KEY,
    after_sale_id   BIGINT NOT NULL REFERENCES after_sales(id),
    order_item_id   BIGINT NOT NULL REFERENCES order_items(id),
    quantity        INTEGER NOT NULL,                      -- 退款数量
    refund_amount   INTEGER NOT NULL,                      -- 退款金额（分）
    UNIQUE(after_sale_id, order_item_id)
);
```

### D1.2 金额单位规约（D-02）

#### D1.2.1 全链路金额规约

| 层 | 存储/传输格式 | 示例 |
|---|---|---|
| PostgreSQL | `INTEGER`（分） | `1999` = ¥19.99 |
| Python 后端计算 | `Decimal`（元），序列化时转为 `int`（分） | `Decimal('19.99')` → API 输出 `1999` |
| API 请求/响应 | `integer`（分） | `"price": 1999` |
| TypeScript 前端 | `number`（分） | `const price = 1999` |
| 前端展示 | `formatPrice(1999)` → `"¥19.99"` | — |

#### D1.2.2 Pydantic 序列化层

```python
# backend/app/core/price.py
from decimal import Decimal, ROUND_HALF_UP
from pydantic import field_serializer, field_validator

CENTS_PER_YUAN = Decimal('100')

def yuan_to_cents(yuan: Decimal) -> int:
    """Decimal(元) → int(分)，四舍五入到分"""
    return int((yuan * CENTS_PER_YUAN).to_integral_value(rounding=ROUND_HALF_UP))

def cents_to_yuan(cents: int) -> Decimal:
    """int(分) → Decimal(元)"""
    return Decimal(cents) / CENTS_PER_YUAN

# Pydantic 模型中使用
class OrderResponse(BaseModel):
    total_amount: int  # 分

    @field_serializer('total_amount')
    def serialize_amount(self, v: int) -> int:
        return v  # 已经是分，直接输出

class OrderCreate(BaseModel):
    # 前端传入也是分
    total_amount: int
```

#### D1.2.3 TypeScript 前端工具函数

```typescript
// packages/shared-types/src/utils/price.ts

/** 分 → 展示字符串 */
export function formatPrice(cents: number, currency = '¥'): string {
  if (!Number.isFinite(cents)) return '-';
  const yuan = cents / 100;
  return `${currency}${yuan.toFixed(2)}`;
}

/** 分 → 元（用于计算） */
export function centsToYuan(cents: number): number {
  return cents / 100;
}

/** 元 → 分（用于提交） */
export function yuanToCents(yuan: number): number {
  return Math.round(yuan * 100);
}

/** 金额类型别名，语义化标注 */
export type Price = number; // 始终为分
```

#### D1.2.4 OpenAPI 字段约定

所有金额字段类型为 `integer`，字段名以 `_amount` / `_price` / `_fee` 结尾，注释标注"单位：分"：

```yaml
# OpenAPI 示例
Order:
  type: object
  properties:
    totalAmount:
      type: integer
      description: 订单总金额，单位：分
      example: 1999
```

### D1.3 购物车一致性设计（D-03）

#### D1.3.1 数据流

```
加购/改数量/删商品
       ↓
   写 Redis（主）
       ↓ 异步
   写 DB（备）
       ↓
  下单时：
  1. 从 DB 读 SKU 最新价格/库存
  2. 与请求中快照金额对比
  3. 不一致返回 PRICE_CHANGED
  4. 一致则创建 order + order_items（快照锁定）
```

#### D1.3.2 Redis 数据结构

```
# 用户购物车
Key:    cart:user:{user_id}
Value:  Hash
  Field: {sku_id}
  Value: JSON { quantity, added_at, stale }

# 游客购物车
Key:    cart:guest:{session_id}
Value:  Hash（同上）

# session_id → user_id 映射（登录合并用）
Key:    cart:session_map:{session_id}
Value:  {user_id}
TTL:    7d
```

#### D1.3.3 游客 → 登录合并流程

```
1. 用户登录成功
2. 读取 cart:guest:{session_id} 和 cart:user:{user_id}
3. 逐 SKU 合并：
   - 两边都有：数量取较大值（上限库存）
   - 仅一边有：直接合并
4. 写入 cart:user:{user_id}
5. 删除 cart:guest:{session_id}
6. 删除 cart:session_map:{session_id}
```

#### D1.3.4 SKU 变更同步

| 触发事件 | 购物车动作 |
|---|---|
| SKU 下架 | Celery 任务标记该 SKU 项 `stale=true, reason='off_shelf'` |
| SKU 改价 | 标记 `stale=true, reason='price_changed'` |
| SKU 库存变化 | 若库存 < 购物车数量，标记 `stale=true, reason='stock_insufficient'`，并调整数量 |
| 前端展示 | `stale=true` 的项标黄/红，提示"价格已变更/已下架/库存不足" |
| 结算校验 | 服务端取 SKU 最新数据，与请求快照对比 |

#### D1.3.5 DB 购物车表（异步落库）

```sql
CREATE TABLE cart_items (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    sku_id      BIGINT NOT NULL REFERENCES skus(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, sku_id)
);

CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
```

#### D1.3.6 下单金额校验

```python
# backend/app/order/service.py
async def create_order(user_id: int, items: list[OrderItemInput]) -> Order:
    # 从 DB 读 SKU 最新数据
    sku_ids = [item.sku_id for item in items]
    skus = await sku_repo.get_by_ids(sku_ids)

    for item_input in items:
        sku = skus[item_input.sku_id]
        # 校验价格
        if sku.price_cents != item_input.price_cents:
            raise ApiError(
                code='PRICE_CHANGED',
                i18n_key='errors.price_changed',
                message=f'商品 {sku.name} 价格已变更，请重新确认',
                field='price_cents',
                details={'sku_id': sku.id, 'old': item_input.price_cents, 'new': sku.price_cents}
            )
        # 校验库存
        if sku.available_stock < item_input.quantity:
            raise ApiError(code='STOCK_INSUFFICIENT', ...)

    # 快照锁定：order_items 存下单时的价格/规格
    order = await order_repo.create(user_id, items, skus)
    # 清购物车对应项
    await cart_service.remove_items(user_id, sku_ids)
    return order
```

### D1.4 RBAC 权限模型（D-04）

#### D1.4.1 一期权限模型（菜单 + 按钮）

```sql
-- 管理员表
CREATE TABLE admins (
    id          BIGSERIAL PRIMARY KEY,
    username    VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name        VARCHAR(50),
    phone       VARCHAR(20),
    avatar      VARCHAR(500),
    is_super    BOOLEAN NOT NULL DEFAULT FALSE,  -- 超级管理员
    status      VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE / DISABLED
    last_login_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 角色表
CREATE TABLE roles (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,     -- super_admin / operator / finance / warehouse
    label       VARCHAR(100) NOT NULL,           -- 超级管理员 / 运营 / 财务 / 仓管
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 管理员-角色关联
CREATE TABLE admin_roles (
    admin_id    BIGINT NOT NULL REFERENCES admins(id),
    role_id     BIGINT NOT NULL REFERENCES roles(id),
    PRIMARY KEY (admin_id, role_id)
);

-- 权限表
CREATE TABLE permissions (
    id          BIGSERIAL PRIMARY KEY,
    parent_id   BIGINT REFERENCES permissions(id),
    type        VARCHAR(10) NOT NULL,            -- MENU / BUTTON
    code        VARCHAR(100) NOT NULL UNIQUE,    -- e.g. 'product:delete', 'order:export'
    name        VARCHAR(100) NOT NULL,           -- e.g. '删除商品', '导出订单'
    path        VARCHAR(200),                     -- 前端路由路径（MENU 类型）
    icon        VARCHAR(50),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 角色-权限关联
CREATE TABLE role_permissions (
    role_id       BIGINT NOT NULL REFERENCES roles(id),
    permission_id BIGINT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);
```

#### D1.4.2 预置角色与权限

| 角色 | 权限范围 |
|---|---|
| 超级管理员 (`super_admin`) | 全部菜单 + 全部按钮 + 系统设置 + 支付配置 + 自定义脚本 |
| 运营 (`operator`) | 商品/订单/低代码/售后/会员菜单 + 对应操作按钮 |
| 财务 (`finance`) | 订单/售后/财务/数据看板菜单 + 导出 + 退款审核按钮 |
| 仓管 (`warehouse`) | 库存/订单(发货)/采购菜单 + 库存调整按钮 |

#### D1.4.3 前端权限组件

```tsx
// packages/admin-app/src/components/Permission.tsx
import { usePermission } from '@/hooks/usePermission';

export function Permission({ code, children, fallback = null }: {
  code: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission } = usePermission();
  return hasPermission(code) ? <>{children}</> : <>{fallback}</>;
}

// 使用
<Permission code="order:delete">
  <Button danger>删除订单</Button>
</Permission>
```

#### D1.4.4 后端权限校验

```python
# backend/app/core/permission.py
from functools import wraps
from fastapi import HTTPException

def require_permission(code: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_admin=Depends(get_current_admin), **kwargs):
            if current_admin.is_super:
                return await func(*args, current_admin=current_admin, **kwargs)
            admin_permissions = await get_admin_permissions(current_admin.id)
            if code not in admin_permissions:
                raise HTTPException(status_code=403, detail='PERMISSION_DENIED')
            return await func(*args, current_admin=current_admin, **kwargs)
        return wrapper
    return decorator

# 使用
@router.delete('/orders/{order_id}')
@require_permission('order:delete')
async def delete_order(order_id: int, current_admin=Depends(get_current_admin)):
    ...
```

#### D1.4.5 二期数据权限预留

二期数据权限扩展方案（一期不实现，仅预留设计）：

```sql
-- 二期新增：角色数据范围
ALTER TABLE roles ADD COLUMN data_scope VARCHAR(20) DEFAULT 'ALL';
-- ALL: 全部数据
-- SELF: 仅自己创建的
-- DEPT: 本部门
-- DEPT_AND_SUB: 本部门及下属
-- CUSTOM: 自定义（role_data_scope_rules 表定义）
```

### D1.5 物流公司枚举与配置（D-05）

#### D1.5.1 shared-types 枚举

```typescript
// packages/shared-types/src/enums/logistics.ts

export const LogisticsCompanyCode = {
  SF: '顺丰速运',
  YTO: '圆通速递',
  ZTO: '中通快递',
  STO: '申通快递',
  YD: '韵达快递',
  JT: '极兔速递',
  EMS: '邮政EMS',
  DBL: '德邦快递',
  JD: '京东物流',
  FAST: '快捷速递',
  OTHER: '其他',
} as const;

export type LogisticsCompanyCodeType = keyof typeof LogisticsCompanyCode;
```

#### D1.5.2 后端配置表

```sql
-- 物流公司配置（后台可扩展）
CREATE TABLE logistics_companies (
    id          BIGSERIAL PRIMARY KEY,
    code        VARCHAR(20) NOT NULL UNIQUE,     -- SF/YTO/ZTO/...
    name        VARCHAR(50) NOT NULL,            -- 顺丰速运
    tracking_url_template VARCHAR(500),           -- https://www.sf-express.com/track?id={tracking_no}
    provider_code VARCHAR(20),                    -- 快递100/快递鸟编码（二期用）
    sort_order  INTEGER NOT NULL DEFAULT 0,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 一期预置数据
INSERT INTO logistics_companies (code, name, tracking_url_template, sort_order) VALUES
('SF', '顺丰速运', 'https://www.sf-express.com/track?id={tracking_no}', 1),
('YTO', '圆通速递', 'https://www.yto.net.cn/track?id={tracking_no}', 2),
('ZTO', '中通快递', 'https://www.zto.com/track?id={tracking_no}', 3),
('STO', '申通快递', 'https://www.sto.cn/track?id={tracking_no}', 4),
('YD', '韵达快递', 'https://www.yundaex.com/track?id={tracking_no}', 5),
('JT', '极兔速递', 'https://www.jtexpress.com.cn/track?id={tracking_no}', 6),
('EMS', '邮政EMS', 'https://www.ems.com.cn/track?id={tracking_no}', 7),
('DBL', '德邦快递', 'https://www.deppon.com/track?id={tracking_no}', 8),
('JD', '京东物流', 'https://www.jdl.com/track?id={tracking_no}', 9);
```

### D1.6 统一主题配置（D-29）

#### D1.6.1 site_themes 表

商城与官网共享同一主题表，通过 `scope` 字段区分：

```sql
CREATE TABLE site_themes (
    id          BIGSERIAL PRIMARY KEY,
    scope       VARCHAR(20) NOT NULL,             -- 'h5' / 'site' / 'global'
    key         VARCHAR(100) NOT NULL,             -- CSS 变量名
    value       VARCHAR(500) NOT NULL,             -- CSS 变量值
    label       VARCHAR(100),                      -- 后台展示名
    group_name  VARCHAR(50),                       -- 分组：color / spacing / border / typography
    sort_order  INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(scope, key)
);
```

#### D1.6.2 预置主题变量

| scope | key | 默认值 | label | group |
|---|---|---|---|---|
| global | --color-primary | #ff6b6b | 主色 | color |
| global | --color-success | #52c41a | 成功色 | color |
| global | --color-warning | #faad14 | 警告色 | color |
| global | --color-error | #ff4d4f | 错误色 | color |
| global | --color-text-primary | #1a1a1a | 主文字色 | color |
| global | --color-text-secondary | #666666 | 辅文字色 | color |
| global | --color-bg-primary | #ffffff | 主背景色 | color |
| global | --border-radius-base | 8px | 圆角基准 | border |
| global | --spacing-base | 16px | 间距基准 | spacing |
| h5 | --h5-tabbar-height | 50px | Tabbar 高度 | spacing |
| h5 | --h5-header-height | 44px | 顶部导航高度 | spacing |
| site | --site-nav-height | 72px | 导航栏高度 | spacing |
| site | --site-footer-bg | #1a1a1a | Footer 背景 | color |

#### D1.6.3 前端主题加载

```typescript
// H5 端启动时
async function loadTheme() {
  const res = await api.get('/api/settings/theme', { params: { scope: 'h5' } });
  const vars = res.data; // [{ key: '--color-primary', value: '#ff6b6b' }, ...]
  vars.forEach(({ key, value }) => {
    document.documentElement.style.setProperty(key, value);
  });
}

// 官网端同理，scope='site'
```

#### D1.6.4 预设主题 seed 落库（2026-09 补充，衔接设计规范 §18.2）

设计规范 §18.2 定义了 5 套预设主题（珊瑚红 #ff6b6b / 商务蓝 #1890ff / 自然绿 #52c41a / 高贵紫 #722ed1 / 稳重橙 #fa8c16），**预设主题只定义主色**，完整变量集按下述流程生成并落库：

```
预设主色（5 套）
  ↓ generateColorScale(primaryHex)（设计规范 §18.1，10 档 50~900）
  + D1.6.2 预置变量默认值（--color-success/--spacing-base 等 13 项）
  ↓ 组成该预设的完整变量集
  ↓ 幂等 seed 脚本（Alembic data migration，UNIQUE(scope, key) upsert）
site_themes 表（scope='global'，key 前缀区分预设：--preset-coral-* / --preset-blue-* 等）
```

**规约**：
- seed 时机：1b 期商城主题配置交付时（plan-14+）随迁移脚本执行，**1a 期不建此表不跑 seed**
- 幂等：重复执行 upsert 不产生重复行（依赖 UNIQUE(scope, key)）
- 商家套用预设：后台调 `/api/admin/settings/theme/apply-preset`，后端取该预设变量集覆盖 `site_themes` 中 scope='h5'/'site' 的当前值（用户自定义项保留逻辑见 1b 拆解时细化）
- 默认主题（珊瑚红）seed 后即为 D1.6.2 默认值本身，商家未配置时前端可不拉取（有内置兜底）

### D1.7 修订后的核心数据表清单

在 v1.1 附录 11.2 基础上，v1.2 新增/修改的表：

| 表名 | 说明 | 变更 |
|---|---|---|
| orders | 订单主表 | **修改**：status 枚举缩减为 5 个正向状态，新增 refund_status 字段，金额字段改为 INTEGER（分） |
| after_sales | 售后单表 | **修改**：status 枚举扩展为 7+1 个独立状态，新增 type 字段 |
| after_sale_items | 售后商品关联表 | **新增** |
| cart_items | 购物车 DB 表 | **新增**（Redis 为主，DB 异步落库） |
| logistics_companies | 物流公司配置表 | **新增** |
| site_themes | 统一主题配置表 | **新增** |
| freight_templates | 运费模板表 | **新增**（见 D6.5） |
| freight_template_items | 运费模板项表 | **新增**（见 D6.5） |
| notifications | 通知记录表 | **新增**（见 D6.1） |
| notification_templates | 通知模板表 | **新增**（见 D6.1） |
| reviews | 商品评价表 | **新增**（见 D6.2） |
| review_images | 评价图片表 | **新增**（见 D6.2） |

---

## D2. 接口契约详细设计

### D2.1 统一响应格式（D-02, D-08）

#### D2.1.1 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... },
  "requestId": "req_abc123"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 0 表示成功，非 0 表示业务错误 |
| message | string | 默认中文消息，前端可基于 i18nKey 替换 |
| data | object/null | 业务数据，错误时为 null |
| requestId | string | 请求追踪 ID（UUID），与日志关联 |

#### D2.1.2 分页响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "size": 20
  },
  "requestId": "req_abc123"
}
```

统一分页参数：
- `page`：从 1 开始
- `size`：默认 20，最大 100
- 排序：`sort=created_at:desc`（字段:方向，多字段用逗号分隔）

#### D2.1.3 错误响应（D-08 三层结构）

```json
{
  "code": 40004,
  "message": "商品价格已变更，请重新确认",
  "i18nKey": "errors.price_changed",
  "field": "price_cents",
  "details": {
    "skuId": 123,
    "oldPrice": 1999,
    "newPrice": 2099
  },
  "requestId": "req_abc123"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| code | integer | 是 | 业务错误码（见 D2.2） |
| message | string | 是 | 默认中文消息 |
| i18nKey | string | 否 | i18n key，前端有翻译时替换 message |
| field | string | 否 | 表单字段错误（用于表单校验高亮） |
| details | object | 否 | 错误详情（不含敏感信息） |
| requestId | string | 是 | 追踪 ID |

#### D2.1.4 HTTP 状态码映射

| HTTP | 场景 | code 范围 |
|---|---|---|
| 200 | 成功 | 0 |
| 400 | 参数错误/校验失败 | 10000-19999 |
| 401 | 未认证/Token 失效 | 40001 |
| 403 | 权限不足 | 40003 |
| 404 | 资源不存在 | 40400 |
| 409 | 状态冲突（如订单已支付） | 40900-40999 |
| 429 | 限流 | 42900 |
| 500 | 服务端错误 | 50000 |

### D2.2 错误码表（D-08）

#### D2.2.1 错误码命名规则

`{HTTP段}{模块}{序号}`，5 位数字：

| 段 | HTTP | 模块 |
|---|---|---|
| 1xxxx | 400 | 参数校验 |
| 2xxxx | 400 | 业务规则 |
| 4xxxx | 401/403/404 | 认证/权限/资源 |
| 429xx | 429 | 限流 |
| 5xxxx | 500 | 服务端 |

#### D2.2.2 核心错误码表

| code | i18nKey | 默认 message | HTTP | 模块 |
|---|---|---|---|---|
| 0 | common.success | ok | 200 | — |
| 10001 | common.param_invalid | 参数错误 | 400 | 通用 |
| 10002 | common.param_missing | 缺少必填参数 | 400 | 通用 |
| 10003 | common.param_type_error | 参数类型错误 | 400 | 通用 |
| 20001 | auth.invalid_credentials | 用户名或密码错误 | 400 | 认证 |
| 20002 | auth.sms_code_invalid | 验证码错误或已过期 | 400 | 认证 |
| 20003 | auth.sms_code_rate_limit | 验证码发送过于频繁 | 429 | 认证 |
| 20004 | auth.token_expired | Token 已过期 | 401 | 认证 |
| 20005 | auth.token_invalid | Token 无效 | 401 | 认证 |
| 20006 | auth.account_disabled | 账号已被禁用 | 403 | 认证 |
| 20101 | product.not_found | 商品不存在 | 404 | 商品 |
| 20102 | product.off_shelf | 商品已下架 | 400 | 商品 |
| 20103 | product.sku_not_found | SKU 不存在 | 404 | 商品 |
| 20201 | cart.empty | 购物车为空 | 400 | 购物车 |
| 20202 | cart.sku_stale | 购物车商品信息已变更 | 400 | 购物车 |
| 20203 | cart.quantity_exceed_stock | 购物车数量超出库存 | 400 | 购物车 |
| 20301 | order.not_found | 订单不存在 | 404 | 订单 |
| 20302 | order.status_conflict | 订单状态冲突 | 409 | 订单 |
| 20303 | order.price_changed | 商品价格已变更 | 400 | 订单 |
| 20304 | order.stock_insufficient | 库存不足 | 400 | 订单 |
| 20305 | order.expired | 订单已超时 | 400 | 订单 |
| 20306 | order.cannot_cancel | 订单当前状态不可取消 | 409 | 订单 |
| 20307 | order.cannot_pay | 订单当前状态不可支付 | 409 | 订单 |
| 20401 | stock.insufficient | 库存不足 | 400 | 库存 |
| 20402 | stock.lock_failed | 库存锁定失败 | 409 | 库存 |
| 20501 | payment.order_paid | 订单已支付 | 409 | 支付 |
| 20502 | payment.amount_mismatch | 支付金额不匹配 | 400 | 支付 |
| 20503 | payment.signature_invalid | 支付签名验证失败 | 400 | 支付 |
| 20504 | payment.refund_failed | 退款失败 | 500 | 支付 |
| 20601 | after_sale.not_found | 售后单不存在 | 404 | 售后 |
| 20602 | after_sale.status_conflict | 售后状态冲突 | 409 | 售后 |
| 20603 | after_sale.amount_exceed | 退款金额超出订单金额 | 400 | 售后 |
| 20701 | upload.file_type_invalid | 文件类型不允许 | 400 | 上传 |
| 20702 | upload.file_too_large | 文件大小超限 | 400 | 上传 |
| 20703 | upload.signature_invalid | 上传签名无效 | 400 | 上传 |
| 20801 | page.schema_invalid | 页面 Schema 格式错误 | 400 | 低代码 |
| 20802 | page.component_not_found | 组件类型不存在 | 400 | 低代码 |
| 40001 | auth.unauthorized | 未登录 | 401 | 认证 |
| 40003 | auth.permission_denied | 权限不足 | 403 | 权限 |
| 40400 | common.not_found | 资源不存在 | 404 | 通用 |
| 40900 | common.conflict | 资源状态冲突 | 409 | 通用 |
| 42900 | common.rate_limited | 请求过于频繁，请稍后重试 | 429 | 限流 |
| 50000 | common.server_error | 服务器内部错误 | 500 | 通用 |
| 50001 | common.service_unavailable | 服务暂时不可用 | 503 | 通用 |

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
