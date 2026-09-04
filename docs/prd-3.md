
## D5. 安全合规详细设计

### D5.1 联系表单字段级加密（D-18）

#### D5.1.1 加密策略

> **分期降级说明（2026-09 修订）**：一期密钥方案为环境变量 `FIELD_ENCRYPTION_KEY`（强随机文件密钥，密钥文件权限 600，不入 git）；轮换时新密钥加密新数据 + `FIELD_ENCRYPTION_KEY_LEGACY` 解密存量。云 KMS 为**增长期**方案（触发条件：日订单 > 2000，见 AGENTS.md §十四 运维能力分期适用矩阵）。降级理由：1a 期为单机 Docker Compose 部署，引入云 KMS 会增加部署依赖与成本，与"轻量"原则矛盾。KMS 迁移路径：`FIELD_ENCRYPTION_KEY` 信封加密化（数据密钥 DEK 加密存储，主密钥换 KMS 托管）→ 存量密文不重写。

- 字段级 AES-256-GCM 加密
- 一期密钥：`FIELD_ENCRYPTION_KEY` 文件密钥；增长期：云厂商 KMS（阿里云 KMS / 腾讯云 KMS）管理
- 应用启动时加载密钥，缓存在内存（每 24h 轮换）
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
- 敏感词过滤（评价模块自带敏感词库 + 过滤函数，随 D6.2 1b 期交付；官网联系表单的反垃圾方案为二期，见难点 17，二者不共用模块）

### D6.3 搜索系统（一期 PG 全文索引）

#### D6.3.1 一期方案：PostgreSQL 全文索引

> **中文分词分期（2026-09 裁决）**：1a 期用 `simple` 配置 + **ILIKE 兜底**（simple 不分词，中文按整串进向量，单字/子串查询走 `name ILIKE '%kw%'` 分支命中），**不部署任何分词扩展**；1b 期升级 zhparser。禁在 1a 环境安装 pg_jieba/zhparser。

```sql
-- products 表增加全文索引字段（1a：simple 配置，英文/数字按词匹配）
ALTER TABLE products ADD COLUMN search_vector tsvector;

-- 触发器自动维护
CREATE TRIGGER products_search_vector_trigger
BEFORE INSERT OR UPDATE ON products
FOR EACH ROW EXECUTE FUNCTION
  tsvector_update_trigger(search_vector, 'pg_catalog.simple', name, description);

CREATE INDEX idx_products_search ON products USING GIN(search_vector);

-- 1a 查询（全文 + ILIKE 兜底双分支：中文子串靠 ILIKE 命中）
SELECT * FROM products
WHERE search_vector @@ to_tsquery('pg_catalog.simple', 'iPhone & 手机')
   OR name ILIKE '%手机%'
ORDER BY ts_rank(search_vector, to_tsquery('pg_catalog.simple', 'iPhone & 手机')) DESC
LIMIT 20;

-- 1b 升级：安装 zhparser 后，触发器改用 zhparser 配置重建 search_vector，ILIKE 分支保留为 fallback
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
        # 注意：1a 期通知中心未上线，该事件暂无消费者，仅下方看板 cache 生效；
        # 1b 随通知中心（D6.1）启用订阅消费，事件发布代码 1a 期即按此写好，无需返工
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
        # 重量数据来源（E3.3）：下单前 freight-calc 接口实时读 skus.weight_grams；
        # 下单后读 order_items.weight_grams 快照（克），模板 first_unit/additional_unit 单位为 kg
        total_weight = sum(Decimal(i.weight_grams) / 1000 * i.quantity for i in items)
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

> **1b 期交付（plan-14+，2026-09 裁决：§7.1 归属 1b）**。API 契约与前端展示（商品详情页"相关推荐"区）1b 启动时随计划补齐，本文仅保留数据模型与后台操作设计，避免过度设计。

#### D6.7.1 手动推荐（1b 交付）

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
# 说明：aws cli 走 S3 兼容 endpoint（阿里云 OSS 支持 S3 协议，
# 配 OSS_PROVIDER=aliyun + endpoint，勿部署 AWS 原生资源）
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
# 说明：aws cli 走 S3 兼容 endpoint（阿里云 OSS 支持 S3 协议，
# 配 OSS_PROVIDER=aliyun + endpoint，勿部署 AWS 原生资源）
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

> **分期说明（2026-09 裁决，对齐 AGENTS.md 运维分期矩阵）**：蓝绿部署为**增长期能力**，1a/1b 期不作基线要求——1a 期验收只要求"回滚脚本演练通过"（E15.2 #28，Docker Compose 重启回滚 + `alembic downgrade -1`）。以下方案为增长期落地设计，1a 期不实施。

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

  # 2. 单元测试 + 覆盖率门禁（对齐 E15.2 #22）
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
      - run: pnpm --filter backend run pytest --cov --cov-fail-under=80
      - name: Frontend coverage gate (≥70%)
        run: pnpm test -- --coverage --coverageThreshold='{"global":{"lines":70}}'

  # 3. 构建
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pnpm install
      - run: pnpm build
      - run: pnpm --filter backend run build

  # 3.5 数据库迁移可逆性验证（对齐 D7.4.1）
  migration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: test
        ports: ['5432:5432']
    steps:
      - uses: actions/checkout@v3
      - run: pnpm --filter backend run alembic upgrade head
      - run: pnpm --filter backend run alembic downgrade -1
      - run: pnpm --filter backend run alembic upgrade head

  # 4. 包体积门禁（1a 期必须）
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

  # 5. a11y 检测（二期门禁；1a/1b 期以 impeccable /audit + axe-core 人工审查替代，见 D8.4）
  a11y:
    runs-on: ubuntu-latest
    needs: build
    if: false  # 二期启用：去掉此行并恢复下方步骤
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

#### D7.5.2 阻止合并规则（1a 期口径）

- 上述任一 job 失败 → 阻止合并到 main（a11y job 二期前为 `if: false` 不参与门禁）
- 首屏 JS gzip > 200KB → 阻止合并
- 覆盖率：后端 < 80% 或前端 < 70% → 阻止合并（对齐 E15.2 #22）
- 迁移不可逆（upgrade/downgrade/upgrade 失败）→ 阻止合并
- 枚举不一致 → 阻止合并
- OpenAPI lint 不通过 → 阻止合并
- a11y 门禁二期接入后纳入阻止合并；1a/1b 期以 plan-12 a11y 终检（impeccable /audit）替代

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
| 商品评价 | 第 3 周 | 评价系统（D-10）、评价审核、评价展示。**内部顺序：通知中心先行、评价随后**（评价审核的"拒绝通知"依赖通知中心已就绪） |
| 商城低代码 | 第 4-5 周 | 三栏搭建器、5 个核心组件、属性面板（内容+样式）、撤销重做（D3.3）、保存/自动保存、预览、页面管理、Schema 版本管理（D3.1） |
| 验证 | 第 5 周 | 端到端验证、性能优化、CI 完善 |

**1b 期 5 个核心低代码组件**：搜索框、轮播图、商品网格、图片广告、辅助空白（其余 5 个二期补齐）

### D8.2 二期范围调整

二期在 v1.1 基础上新增：

- 商城低代码扩展至 10 个组件（补齐公告栏、富文本、商品横滑、优惠券占位、分类导航）
- 优惠券完整实现（满减券/折扣券/无门槛券）
- 操作日志查询页（对齐 E15.1 #17 裁决：1a 只验写入，查询页二期交付）
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
| 🟡 P1 | 1a 期 | D-12 H5 多级缓存、D-13 ISR 事件（接口预留）、D-14 双构建兼容、D-19 支付前置、D-20 文件上传、D-28 限流、D-29 主题统一 |
| 🟡 P1 | 增长期 | D-27 蓝绿部署（对齐 D7.3 分期框注：1a/1b 只验回滚脚本，E15.2 #28） |
| 🟡 P1 | 二期 | D-15 3D 隔离、D-16 分阶段（已完成 1a/1b）、D-17 多租户、D-18 表单加密 |
| 🟢 P2 | 1a 期 | D-24 CI 门禁（**拆分交付**：lint/test/build/bundle-size/contract/enum-sync 门禁 1a 全绿，见 D7.5；a11y 门禁除外） |
| 🟢 P2 | 二期 | D-21 i18n、D-23 a11y（门禁二期接入；1a/1b 以 impeccable /audit + axe-core 人工审查替代，plan-12 a11y 终检）、D-24 CI 门禁的 a11y 部分、D-25 读写分离、D-26 Source Map、D-30 A/B 测试 |
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
    weight_grams    INTEGER,                        -- 单件重量快照（克，下单时取自 skus.weight_grams，按重量计费的运费计算用）
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
