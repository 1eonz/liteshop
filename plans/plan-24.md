# Plan 24：PostgreSQL/Redis 集成、并发测试与商业验收

> PRD 章节：E3.1.2+E12+E15+E16.7

## 任务清单
- [x] 启动 PostgreSQL 16 和 Redis 7，执行健康检查。
- [x] 执行 Alembic 全量迁移、回滚和空库启动检查（本地数据库已验证可逆迁移）。
- [x] 增加真实 PostgreSQL/Redis fixture，避免只依赖内存模式。
- [x] 增加并发下单、库存竞争、支付回调竞态、购物车失败、验证码消费、refresh token 轮换和收藏幂等测试。
- [ ] 增加下架下单、退款重试和主题一致性测试（Token 重放已由真实 Redis 轮换测试覆盖）。
- [x] 补齐 shared-types/tokens/components 行为测试。
- [x] 执行 backend、H5、Admin、shared、E2E 全量验证（Docker 集成项除外）。
- [x] 执行契约对照、机械 Impeccable detector 和代码结构审查。
- [x] 增加真实 HTTP API 边界测试和 H5 浏览器真实接口联调：分页、空搜索、非法参数、404、匿名鉴权、CORS 和 Demo fallback 隔离。
- [x] 生成商业验收报告和当前阶段交接文档。
- [x] 启动 Docker Engine，执行真实 PostgreSQL/Redis 健康检查和并发集成测试。

## 验收标准
- [x] 所有本地必需测试通过；后端覆盖率已达 83%，超过 CI 80% 门禁。真实支付/短信/物流供应商仍未接入，生产上线仍需外部供应商沙箱与人工安全复核。

## 2026-09-09 收口记录

- `docker compose ps`：PostgreSQL 16 与 Redis 7 均 `healthy`。
- `LITESHOP_RUN_INTEGRATION=1` + `LITESHOP_USE_DATABASE=true`：真实集成测试 `3 passed`。
- workspace 构建、类型、Lint、单测、19 份 OpenAPI 解析和 `npx impeccable detect` 均通过。

## 2026-09-12 增量记录

- `docker compose ps`：PostgreSQL 16 与 Redis 7 均 `healthy`。
- `LITESHOP_RUN_INTEGRATION=1` + `LITESHOP_USE_DATABASE=true`：真实集成测试 `9 passed`，并连续重复 5 轮验证竞态稳定性。
- 新增真实场景：并发下单库存竞争、支付回调与超时取消竞态、验证码单次消费、refresh token 原子轮换与重放拒绝、购物车请求幂等/Redis 故障映射、收藏 Redis+数据库幂等。
- 修复 `ProductRepository` 与 `InventoryRepository` 异步查询关系预加载缺失导致的 `MissingGreenlet`；所有后端静态检查与单元测试保持通过。
- 当前覆盖率仍约 62%，低于 CI 80% 门禁；未通过配置排除或跳过测试规避。

## 2026-09-13 覆盖率收口记录

- [x] 新增订单超时/ISR、页面/导航/营销数据库分支及后台/用户/运费/退款仓储行为测试。
- [x] `ruff format --check .`、`ruff check .`、`python -m mypy .` 全通过。
- [x] 后端全量测试 `133 passed`，覆盖率 `83%`，超过 CI 80% 门禁。
- [ ] 真实微信/支付宝、短信、物流供应商沙箱及完整 axe-core/i18n 仍未完成，不能据此宣称生产就绪。

## 2026-09-15 真实接口联调记录

- [x] `backend/integration_tests/test_real_http_api.py`：真实数据库模式 HTTP ASGI 测试 3 passed，覆盖商品分页、空搜索、参数边界、404、分类和匿名订单鉴权。
- [x] `tests/e2e/specs/real-api.spec.ts`：Playwright API 与 H5 分类页面真实请求 3 passed；页面实际命中 `/categories` 和 `/products`，不把 Demo fallback 当作通过。
- [x] E2E 支持 `E2E_H5_PORT`、`E2E_ADMIN_PORT`、`E2E_SITE_PORT`、`E2E_API_BASE`，避免复用其他项目占用的开发端口。
- [x] 开发环境 CORS 增加 `127.0.0.1` 默认端口，修复浏览器预检 400。
- [ ] 当前机器 Docker Desktop 引擎停止，需恢复后重跑 PostgreSQL/Redis 集成测试；本轮未修改生产配置。
