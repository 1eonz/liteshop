# Plan 16：购物车一致性、清理与并发测试

> PRD 章节：D1.3+E3.3+E16.3+E16.7

## 任务清单
- [x] 为 Redis 购物车定义原子幂等策略，避免脚本成功而幂等失败。
- [x] 限制单 SKU 和用户购物车总件数，重复请求也不能突破上限。
- [x] 订单成功后清理 Redis 中已结算商品，失败时保留购物车。
- [x] H5 未登录提交订单阻止并跳转登录，不得伪造成功。
- [x] 购物车异常统一返回 code/i18nKey/message/requestId。
- [x] 增加 Redis/DB 失败、重复加购、超量、下单清理测试。
- [x] 更新 cart OpenAPI、shared-types 和前端错误态。

## 验收标准
- [x] 重试不重复累加，订单成功后本地与 Redis 一致。

## 主 Agent 验收记录

- 后端：`ruff check .`、`mypy .`、`pytest -q`，33 passed。
- H5：`tsc --noEmit`、ESLint、Vitest（1 passed）、Vite build、Prettier 均通过。
- 额外修复：购物车 Redis 幂等 key 按 add/update/remove 动作隔离，避免同一 requestId 跨动作复用。
