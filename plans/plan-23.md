# Plan 23：H5/Admin 一期缺失页面与服务化收藏

> PRD 章节：7.1+4.1+4.2+E15.1

## 任务清单
- [x] H5 手机号短信登录接入真实 auth API、倒计时和错误态。
- [x] H5 地址管理、订单详情操作、退款申请、通知入口。
- [ ] H5 搜索历史、热门搜索和分页结果（搜索 API 已支持 q，历史 UI 留后续优化）。
- [x] 收藏从 localStorage 升级服务端 API。
- [x] Admin 会员、评价、低代码页面接入集中 routes/service/hooks/store。
- [x] 所有新增写按钮使用 useDebounceAction，列表具备 loading/empty/error。
- [x] 删除 window.location.pathname 路由分支，统一 React Router v6。
- [x] 补齐新增类型和 token 约束，未新增 any。
- [x] 运行 H5/Admin typecheck、lint、test、build 和 Prettier 验证。

## 验收标准
- [x] H5 与 Admin 一期主路径可完整操作；搜索历史和真实第三方上传仍列为后续增强。

## 主 Agent 验收记录

- 收藏服务化、会员/评价/通知/低代码页面入口已接入；新增模型和迁移已通过后端静态检查。
- H5/Admin 构建与类型检查通过，JSX 由 Prettier 保持多行可读格式。
