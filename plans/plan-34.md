# Plan 34：官网画布与动画配置闭环

> PRD 章节：4.4.1+4.4.4+4.4.5+4.4.6+4.5+D3.3+D3.4
> 当前状态：主要链路已完成；页面搭建器已完成模型、视图和历史/自动保存 hooks 拆分，真实数据库种子发布 E2E 仍待补
> 依赖关卡：Lenis、GSAP、Framer Motion 等依赖必须先确认包体积、许可证和性能预算。

## 目标

补齐 Admin 官网画布、官网组件面板、SEO/动画属性编辑与官网端消费，完成发布到浏览器的闭环。

## 任务清单

- [x] 将 page-builder 的商城/官网模式拆为明确配置，支持 375px 商城画布与 1200px 官网画布切换。
- [x] 按领域拆分 ComponentPalette、Canvas、PropsPanel、History/AutoSave hooks，页面只负责编排。
- [x] 将默认 Schema、组件分组、模板、草稿恢复和预览工具移入 `pages/page-builder/model/page-builder-model.ts`，先建立稳定领域边界。
- [x] 官网模式提供 PRD 定义的组件面板、分组、默认配置和整页模板，不复用不兼容的商城交互。
- [x] 属性面板增加 SEO 与动画配置；Schema 保持版本化并支持迁移。
- [x] SiteRenderer 消费动画字段，支持 reduced motion、组件卸载清理和服务端渲染安全。
- [ ] 新动画依赖在获得确认后按需加载；未确认前只完成无依赖的画布、Schema 和配置链路。
- [x] 发布流程保持 DRAFT/PUBLISHED、channel 隔离、ISR tag/path 失效和失败提示。
- [x] 增加官网画布编辑、保存、发布、公开读取和 ISR 刷新鉴权的浏览器 E2E；真实数据库种子发布与回滚 E2E 待补。
- [x] 检查首屏 JS、LCP、CLS 和移动设备降级，动画不得阻塞主要内容。

## 验收标准

- [x] Admin 可用官网组件搭建 1200px 页面并发布，官网浏览器能读取同一 Schema。
- [x] 动画关闭或 reduced motion 时内容完整可用，无焦点丢失和滚动锁死。
- [x] 未经确认不安装新依赖、不修改 AGENTS.md 技术栈条款。

## 验证命令

```powershell
cd packages\admin-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build

cd ..\site-app
pnpm typecheck
pnpm lint
pnpm test
pnpm build

cd ..\..\tests\e2e
pnpm test
```
