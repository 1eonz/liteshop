# Plan 32：售后完整闭环

> PRD 章节：4.2.7+D1.1.2+D1.3.6+E3.8+E16.3+E16.7
> 当前状态：待开始
> 风险等级：高。退款金额、状态机、库存回补和迁移完成后必须人工复核。

## 目标

在现有退款执行能力之上补齐售后单、审核、退货和退款的完整闭环，不重复实现退款渠道与库存服务。

## 任务清单

- [ ] 核对 `docs/api-contracts/v1/after-sale.yaml`、退款契约和共享枚举；字段不足时先提出契约变更，不擅自修改。
- [ ] 增加 `after_sales` 模型与 Alembic 迁移，包含订单/订单项、类型、状态、申请金额（整数分）、原因、凭证、退货地址/物流、审核信息和时间字段。
- [ ] 建立唯一约束与索引，保证同一订单项的进行中售后不重复创建，`client_request_id` 可兜底幂等。
- [ ] 实现售后状态机和非法流转拒绝，覆盖仅退款、退货退款、换货的有效路径。
- [ ] 后端严格使用 `api → services → repositories → models`，所有写操作进入事务并复用现有退款/库存服务。
- [ ] H5 增加售后申请、列表和详情入口，写操作使用 `useDebounceAction`，mutation `retry: 0`。
- [ ] Admin 增加待审核列表、详情、同意/拒绝、退货信息和确认收货操作，记录操作日志。
- [ ] 退货入库时按售后单幂等回补库存和流水，重复回调/重复点击不重复入库或退款。
- [ ] 增加状态机、越权、金额上限、重复申请、并发审核、退款失败与重试测试。
- [ ] 同步 shared-types 与既有 OpenAPI 契约；若需字段或枚举变更，停在契约确认关卡。

## 验收标准

- [ ] 从 H5 申请到 Admin 审核、退货入库、退款成功/失败可完整追踪。
- [ ] 金额全链路使用整数分，退款总额不超过可退金额。
- [ ] 同一逻辑动作并发执行最多产生一个售后单、一次库存回补和一次退款。
- [ ] 非法状态流转、越权访问和重复审核均返回统一 ApiError。

## 验证命令

```powershell
cd backend
ruff check .
ruff format --check .
pytest -q --cov=app --cov-report=term-missing

cd ..\packages\h5-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build

cd ..\admin-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build
```
