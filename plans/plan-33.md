# Plan 33：H5 Schema 真实数据消费

> PRD 章节：4.3+D3.1+D3.2+D6.3+E2.3+E15
> 当前状态：待开始

## 目标

让后台保存/发布的商城 Schema 在 H5 首页真实渲染，补齐商品、分类、轮播等关键组件的数据消费和页面状态。

## 任务清单

- [ ] 盘点 SchemaRenderer 已实现组件、占位组件和重复组件，优先复用现有 ProductCard、反馈状态与 catalog features。
- [ ] 将 SchemaRenderer 拆为组件注册表、数据适配层和表现组件，避免在一个 switch 中混入查询、转换与视图。
- [ ] ProductGrid/ProductList/ProductCarousel 通过 React Query 消费商品 API，支持 Schema 配置的数量、排序、分类和商品 ID。
- [ ] CategoryGrid 消费分类 API，Carousel/Image/RichText 做 URL 与富文本白名单校验。
- [ ] H5 首页读取已发布首页 Schema；请求失败或无 Schema 时使用明确的安全兜底页面。
- [ ] 每个数据组件提供 Skeleton、EmptyState、ErrorState，不用占位文字冒充业务内容。
- [ ] 未知组件和旧版本 Schema 安全降级，迁移失败不影响其余组件渲染。
- [ ] 补组件注册、数据映射、旧 Schema 迁移、空数据、错误态和首页回退单测。
- [ ] 增加后台发布商城页后 H5 首页消费的 Playwright 流程；测试数据与业务代码分离。
- [ ] 检查首屏 bundle 与请求瀑布，非首屏重组件使用 lazy/Suspense。

## 验收标准

- [ ] 后台发布的商品/分类/轮播配置可在 H5 首页还原为真实内容。
- [ ] 所有视觉值来自 Design Tokens，无硬编码色值、字号、间距、圆角和阴影。
- [ ] 不在 SchemaRenderer 重复定义领域类型、API 路径或商品组件。

## 验证命令

```powershell
cd packages\h5-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build

cd ..\..\tests\e2e
pnpm test
```
