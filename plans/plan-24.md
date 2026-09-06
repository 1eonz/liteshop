# Plan 24：PostgreSQL/Redis 集成、并发测试与商业验收

> PRD 章节：E3.1.2+E12+E15+E16.7

## 任务清单
- [ ] 启动 PostgreSQL 16 和 Redis 7，执行健康检查。
- [ ] 执行 Alembic 全量迁移、回滚和空库启动检查。
- [ ] 增加真实 PostgreSQL/Redis fixture，避免只依赖内存模式。
- [ ] 增加并发下单、库存竞争、支付回调竞态、购物车失败和验证码测试。
- [ ] 增加下架下单、退款重试、Token 重放和主题一致性测试。
- [ ] 补齐 shared-types/tokens/components 行为测试。
- [x] 执行 backend、H5、Admin、shared、E2E 全量验证（Docker 集成项除外）。
- [x] 执行契约对照、机械 Impeccable detector 和代码结构审查。
- [x] 生成商业验收报告和 `docs/交接文档-一期阶段.md`。
- [ ] 启动 Docker Engine，执行真实 PostgreSQL/Redis 迁移、健康检查和并发集成测试。

## 验收标准
- [ ] 所有必需测试通过；当前因 Docker Engine 无响应，生产阻塞项明确禁止上线。
