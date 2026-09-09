# Plan 24：PostgreSQL/Redis 集成、并发测试与商业验收

> PRD 章节：E3.1.2+E12+E15+E16.7

## 任务清单
- [x] 启动 PostgreSQL 16 和 Redis 7，执行健康检查。
- [x] 执行 Alembic 全量迁移、回滚和空库启动检查（本地数据库已验证可逆迁移）。
- [x] 增加真实 PostgreSQL/Redis fixture，避免只依赖内存模式。
- [ ] 增加并发下单、库存竞争、支付回调竞态、购物车失败和验证码测试（当前已覆盖库存竞争，其他路径待补）。
- [ ] 增加下架下单、退款重试、Token 重放和主题一致性测试。
- [x] 补齐 shared-types/tokens/components 行为测试。
- [x] 执行 backend、H5、Admin、shared、E2E 全量验证（Docker 集成项除外）。
- [x] 执行契约对照、机械 Impeccable detector 和代码结构审查。
- [x] 生成商业验收报告和当前阶段交接文档。
- [x] 启动 Docker Engine，执行真实 PostgreSQL/Redis 健康检查和并发集成测试。

## 验收标准
- [ ] 所有必需测试通过；当前后端覆盖率为 59%，低于 CI 80% 门禁，且真实支付/短信/物流供应商未接入，禁止生产上线。

## 2026-09-09 收口记录

- `docker compose ps`：PostgreSQL 16 与 Redis 7 均 `healthy`。
- `LITESHOP_RUN_INTEGRATION=1` + `LITESHOP_USE_DATABASE=true`：真实集成测试 `3 passed`。
- workspace 构建、类型、Lint、单测、19 份 OpenAPI 解析和 `npx impeccable detect` 均通过。
