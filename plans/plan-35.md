# Plan 35：Admin 契约欠账与管理页面

> PRD 章节：4.2.3+4.2.4+4.2.10+D1.4+D6.2+D6.5.3+E7.1+E15
> 当前状态：核心功能完成，专项测试待补

## 目标

优先补齐 1a 的订单改地址、运费模板管理，再完成评价审核、官网导航/全局设置和 RBAC 管理页面。

## 任务清单

- [x] 核对订单改地址 API 契约；仅允许待发货且未进入不可变履约阶段的订单修改地址。
- [x] Admin 订单详情增加地址编辑抽屉、校验、确认提示、幂等 request id 和操作日志。
- [x] 实现运费模板列表、新建、编辑、复制、启停和删除 UI，金额/阈值使用整数分并复用既有 API。
- [x] 实现评价待审核列表、详情、通过/拒绝，权限与审计完整；商家回复仍待后端契约。
- [x] 实现官网导航与全局设置表单，区分草稿/发布或即时生效字段，避免静默覆盖。
- [x] 实现管理员、角色、权限分配写页面；角色创建/编辑/删除保护和管理员角色绑定均有服务端权限校验、幂等和审计。
- [x] 页面按 pages/components/features/service/store/hooks/utils/router 分层，查询用 React Query，写操作 `retry: 0`。
- [x] 所有写操作按钮使用 `useDebounceAction`，表单错误与服务端 ApiError 可定位到字段。
- [ ] 补权限拒绝、编辑冲突、空状态、分页和写操作失败恢复浏览器测试。

## 验收标准

- [x] 1a 的订单改地址与运费模板管理有可用 UI 和操作日志。
- [x] 评价回复/审核、导航/设置、RBAC 页面不直接调用裸 axios，不在组件内定义重复 DTO。
- [ ] Admin 关键流程具备 Playwright 覆盖和键盘可达性。

## 验证命令

```powershell
cd packages\admin-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build

cd ..\..\tests\e2e
pnpm test
```
