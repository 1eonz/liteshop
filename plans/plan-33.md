# Plan 33：H5 Schema 真实数据消费

> PRD 章节：4.3+D3.1+D3.2+D6.3+E2.3+E15
> 当前状态：**进行中（刷新/骨架和 Schema 配置消费已完成，真实数据库发布 E2E 与性能深测仍待补）**

## 目标

让后台保存/发布的商城 Schema 在 H5 首页真实渲染，补齐商品、分类、轮播等关键组件的数据消费和页面状态。

## 任务清单

- [x] 盘点 SchemaRenderer 已实现组件、占位组件和重复组件，复用现有 ProductCard、反馈状态与 catalog features。
- [x] 将 SchemaRenderer 收口为组件注册表、props 适配函数和表现组件，页面不再维护第二套首页 JSX。
- [x] ProductGrid/ProductList/ProductCarousel 通过 React Query 消费商品 API，支持 Schema 配置的数量、列数、排序和商品 ID；分类过滤保留为后续 Schema 字段扩展。
- [x] CategoryGrid 消费分类 API，Carousel/Image URL 做协议白名单校验，RichText 仅渲染纯文本。
- [x] H5 首页读取已发布首页 Schema；网络失败使用同一套默认 Schema，无 Schema 时显示明确空状态。
- [x] 每个数据组件提供加载、空数据和错误状态。
- [x] 未知组件安全降级，Schema 组件 ID 缺失时使用稳定回退 key；查询层归一化不再覆盖合法后台 Schema。
- [x] Carousel 支持配置化自动播放、手动切换、指示器、站内/外部安全跳转，并尊重 reduced-motion。
- [x] 补首页默认 Schema、组件顺序和渲染链路单测。
- [x] 接入首页下拉刷新与骨架屏专用版式；刷新期间保持首屏几何尺寸稳定并提供状态提示。
- [x] 增加后台发布商城页后 H5 首页消费的 Playwright 流程；通过响应隔离验证 H5 消费已发布 Schema。
- [ ] 检查首屏 bundle 与请求瀑布，非首屏重组件使用 lazy/Suspense。

## 验收标准

- [x] 后台发布的商品/分类/轮播配置可在 H5 首页还原为真实内容。
- [x] 所有视觉值来自 Design Tokens，无新增硬编码视觉值。
- [x] 不在 SchemaRenderer 重复定义领域类型、API 路径或商品组件。

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
