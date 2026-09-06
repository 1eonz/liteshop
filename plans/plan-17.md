# Plan 17：主题持久化、设置、搜索、库存分页与真实看板

> PRD 章节：4.2.1+4.2.10+D6.4+D6.5.3+E5.4

## 任务清单
- [x] 建立主题/系统设置表及可逆 Alembic 迁移。
- [x] 主题读写使用数据库事务和幂等键，重启与多实例一致。
- [x] 设置保存失败显示错误，成功后刷新服务端数据。
- [x] 后台商品 q 参数贯穿 API、service、repository。
- [x] 库存分页返回 items/page/pageSize/total/hasNext。
- [x] 看板统计真实销售额、订单数、商品数、库存预警和 UTC 趋势。
- [x] 更新 settings/admin 契约、shared-types 和测试。

## 验收标准
- [x] 无静态趋势或静默演示回退替代真实数据。

## 主 Agent 验收记录

- 后端：`ruff check .`、`mypy .`、`pytest -q`，33 passed。
- Admin：TypeScript、ESLint、Vitest（1 passed）、Vite build、Prettier 均通过。
- 迁移：新增 `20260906_090000_system_settings`，支持 upgrade/downgrade。
