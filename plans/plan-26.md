# Plan 26：后端分层与关键路径测试收口

> PRD 章节：E1.2+E3.1~E3.8+E11.5+E15+E16

## 背景

后端当前可以通过 Ruff、mypy 和 33 条自动化测试，但结构扫描确认若干 API/Service 文件跨越多个领域，部分 Service 直接执行 ORM 持久化操作；测试总覆盖率为 60%，真实数据库关键路径覆盖明显不足。该计划与 plan-24 的 PostgreSQL/Redis 集成验收配套执行。

## 任务清单

- [ ] 将 `api/admin.py` 按商品、分类、订单、库存、会员、RBAC、审计和设置拆分为独立路由模块。
- [ ] 将 `api/orders.py` 按订单查询/创建、支付、运费、售后动作拆分，保持 `/api/v1` 契约路径不变。
- [ ] 将 `services/admin.py` 按领域拆分，禁止通用 Admin Service 聚合全部后台业务。
- [ ] 把收藏、运费、会员、通知、页面、评价、用户资料等 Service 中的 ORM 增删改查下沉到 Repository；Service 只编排业务规则和事务。
- [ ] 复核所有写操作的事务边界、`FOR UPDATE`/条件更新、失败回滚、幂等记录和操作日志写入顺序。
- [ ] 使用真实 PostgreSQL/Redis fixture 覆盖库存竞争、并发下单、支付回调竞态、验证码消费、refresh token 轮换、购物车与收藏幂等。
- [ ] 将订单工作流、库存/支付仓储、退款、会员、通知、评价等关键模块分支覆盖率提升到可审查水平；不得用 `.skip` 或删除断言提高通过率。
- [ ] 对真实迁移执行 `upgrade head → downgrade → upgrade head`，验证空库启动和数据约束。
- [ ] 同步 OpenAPI、共享类型、错误码和迁移文档，确保拆分不改变外部契约。

## 验收标准

- [ ] 后端依赖方向严格保持 `api → services → repositories → models`，API 不直连仓储，Service 不承担持久化细节。
- [ ] 单个 API/Service 文件不再聚合多个无关领域；超大文件必须有清晰的单一领域理由。
- [ ] PostgreSQL 16 与 Redis 7 真实集成测试全绿，迁移可前进、可回滚、可再次升级。
- [ ] 订单、库存、支付、认证关键路径的并发、幂等、金额和非法状态流转均有数据库级测试。
- [ ] `ruff format --check . && ruff check . && mypy . && pytest -v --cov=app --cov-report=term-missing` 全部通过。

