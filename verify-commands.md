# LiteShop 各端验证命令清单

> 子 Agent 完成后必须运行对应命令，把真实输出粘进 final summary。
> 主 Agent 5 步验收时自己再跑一遍。

## 后端（backend/）

```bash
cd backend
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate

# 代码规范
ruff check .

# 类型检查
mypy .

# 单元测试 + 覆盖率
pytest -v --cov=app --cov-report=term-missing

# 数据库迁移可升可降
alembic upgrade head && alembic downgrade -1 && alembic upgrade head

# 关键业务测试
pytest tests/test_order_state_machine.py tests/test_stock_concurrency.py tests/test_payment_callback.py -v

# 契约测试
pytest tests/contract/ -v

# 服务能启动
uvicorn app.main:app --port 8000 &
curl -f http://localhost:8000/health
curl -f http://localhost:8000/ready
kill %1
```

## H5 商城端（packages/h5-app/）

```bash
cd packages/h5-app

# 类型检查
tsc --noEmit

# ESLint
eslint src --ext .ts,.tsx

# 单元测试
pnpm test -- --coverage

# 生产构建
pnpm build

# 包体积检查（gzip 后首屏 JS ≤ 200KB）
gzip -c dist/assets/*.js | wc -c
```

## 管理后台（packages/admin-app/）

```bash
cd packages/admin-app

# 类型检查
tsc --noEmit

# ESLint
eslint src --ext .ts,.tsx

# 单元测试
pnpm test -- --coverage

# 生产构建
pnpm build
```

## 官网端（packages/site-app/，二期）

```bash
cd packages/site-app

# 类型检查
tsc --noEmit

# 构建（SSG）
pnpm build

# 验证 SSG 页面
ls .next/server/app/

# 启动后验证
pnpm start &
curl -f http://localhost:3000
curl -f http://localhost:3000/sitemap.xml
kill %1
```

## 共享层（packages/shared-*）

```bash
# shared-types
cd packages/shared-types && pnpm build && pnpm test

# shared-tokens
cd packages/shared-tokens && pnpm build

# shared-components
cd packages/shared-components && pnpm build && pnpm test

# 双构建兼容性测试
pnpm test:e2e:vite
pnpm test:e2e:nextjs
```

## 端到端（tests/e2e/）

```bash
# 启动基础设施
docker compose up -d postgres redis

# 启动后端
cd backend && uvicorn app.main:app --port 8000 &

# 启动 H5
cd packages/h5-app && pnpm dev --port 5173 &

# 启动 Admin
cd packages/admin-app && pnpm dev --port 5174 &

# 跑 Playwright
cd tests/e2e && pnpm playwright test

# 冒烟测试（部署后）
pnpm playwright test --grep @smoke
```

## a11y 检查

```bash
pnpm --filter shared-components run test:a11y
pnpm --filter h5-app run test:a11y
```

## OpenAPI 契约校验

```bash
npx @stoplight/spectral-cli lint docs/api-contracts/v1/*.yaml
```

## 枚举同步检查

```bash
python scripts/check_enum_sync.py
```

## 包体积门禁

```bash
# H5 首屏 JS gzip 不超过 200KB
SIZE=$(gzip -c packages/h5-app/dist/assets/*.js | wc -c)
if [ $SIZE -gt 204800 ]; then
  echo "H5 首屏 JS gzip ${SIZE} bytes 超过 200KB 限制"
  exit 1
fi
```
