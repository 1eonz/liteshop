version: 1.0

# LiteShop 电商 Profile

## 项目类型识别条件
- L2 依赖：FastAPI、SQLAlchemy/Alembic、Redis、PostgreSQL、pnpm、Turborepo
- L3 PRD：商品、SPU、SKU、库存、购物车、订单、支付、退款、运费
- L4 代码：backend/app、packages/shared-*、packages/h5-app、packages/admin-app

## 专属风险检测项
| 风险 | 检测方式 | 严重度 |
|---|---|---|
| 订单状态机竞态 | 检查超时取消、支付回调、发货/取消是否使用合法流转和并发保护 | 高 |
| 库存超卖 | 检查锁定、扣减、回滚是否使用原子 SQL 条件和事务 | 高 |
| 支付回调幂等 | 检查 `_requestId`、支付流水唯一键、金额校验和重复回调处理 | 高 |
| 金额精度 | 检查数据库整数分、Python Decimal、API 整数分序列化是否全链路一致 | 高 |
| 写操作防抖 | 检查下单、支付、加购、后台发货/改价是否 loading disabled 且 retry=0 | 中 |
| 数据库迁移可逆 | 检查 Alembic 命名、downgrade、危险变更和迁移测试 | 高 |
| 契约漂移 | 对照 docs/api-contracts/v1 与 shared-types、前后端调用方 | 高 |
| 生产配置泄漏 | 检查 .env、支付/OSS/短信密钥是否只存在环境变量 | 高 |

## 专属 PRD 关键词（追加到自适应探测）
- 商品 / SPU / SKU / 库存 / 购物车
- 订单 / 支付 / 退款 / 运费 / 物流 / 幂等
- 1a / MVP / 状态机 / 原子扣减 / 防超卖

## 专属验收项
- 1a MVP 只覆盖 PRD §7.1 标注 `[1a]` 的项目，不把 `[1b]` 混入
- OpenAPI 契约、shared-types、错误码表三者一致
- 订单状态机非法流转被拒绝，合法流转具备并发保护
- 库存锁定/扣减/回滚无超卖，事务失败可回滚
- 支付回调验签、金额校验、幂等和重复回调测试通过
- 所有金额 API 使用整数分，前端展示统一 formatPrice
- 每个子 Agent 通过 5+1 验收后再提交 Conventional Commit
