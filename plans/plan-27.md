# Plan 27：官网 Next.js 低代码渲染与 SEO

> PRD 章节：4.4.1+4.4.4+4.4.5+4.4.6

## 任务清单

- [x] 使用 App Router 实现首页与 `[slug]` 动态路由。
- [x] 增加 `generateStaticParams`、`generateMetadata`、sitemap、robots 与 404。
- [x] 建立官网 Schema 类型与安全渲染器，覆盖 18 类官网组件。
- [x] 导航移动端抽屉、FAQ、联系表单、CTA 等交互满足键盘与焦点可见性要求。
- [x] 所有视觉值使用 Design Tokens，支持响应式和 `prefers-reduced-motion`。
- [x] 页面内容由数据 Schema 驱动，为后续 API/ISR 接入保留边界。

## 验收标准

- [x] `pnpm --filter @liteshop/site-app typecheck && pnpm --filter @liteshop/site-app lint && pnpm --filter @liteshop/site-app test && pnpm --filter @liteshop/site-app build` 全部通过。
- [x] `/`、`/about`、`/products`、`/contact` 可生成静态页面，未知 slug 返回 404。
- [x] 320px 宽度无横向滚动，表单有标签、错误反馈和提交中状态。
