# Plan 28：官网联系表单、导航与全局设置后端

> PRD 章节：4.4.2+4.4.3+D1.6+D2.4

## 任务清单

- [x] 联系表单 DTO、反垃圾蜜罐、限流和幂等 API。
- [x] `form_submissions` PostgreSQL 表、Repository、Service 与迁移。
- [ ] 导航菜单与 Footer 配置持久化及后台权限校验。
- [ ] 官网全局设置与主题令牌读取/更新接口。
- [ ] OpenAPI、错误码和前端 API 出口同步。
- [x] 真实 PostgreSQL 写入与迁移升级测试。

## 验收标准

- [x] 联系表单重复请求只产生一条记录，蜜罐字段非空时拒绝。
- [x] 迁移可 `upgrade/downgrade/upgrade`，服务层不直接操作 ORM。
- [x] 后端 Ruff、mypy、pytest 全部通过。
