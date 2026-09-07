# Plan 22：商城低代码 Schema、渲染器与搭建器

> PRD 章节：4.3+D3.1+D3.2+E2.3+E8.2
> 当前状态：**部分完成**。Schema 与编辑器外壳已交付，H5 关键组件真实数据消费和首页 Schema 接入仍由 plan-33 接续。

## 任务清单
- [x] 定义 10 个商城组件 Schema、version、内容/样式配置和预设。
- [x] shared-types 导出 PageSchema、ComponentSchema 和枚举。
- [x] 后端页面读取、保存、设首页 API，Schema 存 JSON 并支持迁移版本。
- [x] Schema 校验未知组件、危险 URL、超长组件数量和非法 CSS。
- [x] H5 SchemaRenderer 映射安全组件，未知组件显示安全空态。
- [x] Admin 基础搭建器支持添加/排序/删除。
- [x] 实现 50 步撤销基础能力；复制、重做、缩放留待后续视觉编辑增强。
- [ ] 内容/样式 Tab、自动保存和新窗口预览需接入页面保存 API。
- [ ] 通用/服装/生鲜三套商城模板需补齐预设数据。
- [x] 完成类型、lint、构建验证；a11y/Impeccable 终检在商业验收阶段执行。

## 验收标准
- [x] 视觉值使用 Design Tokens，旧 Schema 可通过 version 字段迁移且不丢数据。

## 主 Agent 验收记录

- 新增页面模型、可逆迁移、Schema DTO 校验、页面服务及 H5/Admin 基础渲染和编辑器。
- 仍需补齐编辑器保存/预览和模板预设，已明确列为未完成项。
