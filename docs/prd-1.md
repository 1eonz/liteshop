
## 八、技术难点

### 8.1 商城端难点

#### 难点 1：订单状态机与并发控制

**问题**：订单状态多（待付款/待发货/已发货/已完成/已取消/退款中/已退款），状态流转规则复杂，并发下容易出现状态错乱（如用户同时取消订单和支付成功）。

**解决方案**：
- 定义明确的状态流转图，每个状态只能流向指定的下一个状态
- 用数据库乐观锁（`UPDATE orders SET status=:new WHERE id=:id AND status=:old`），检查影响行数，为 0 则抛出状态冲突异常
- 关键操作（支付回调、取消、发货）加 Redis 分布式锁（按订单号加锁）
- 所有状态变更记录操作日志（谁/什么时间/从什么状态到什么状态/原因）

#### 难点 2：库存超卖

**问题**：高并发下多个用户同时下单同一 SKU，先查库存再扣减会导致超卖。

**解决方案**：
- 原子扣减：`UPDATE sku SET stock = stock - :qty WHERE id = :id AND stock >= :qty`，检查影响行数
- 库存分三层：可用库存（展示）、锁定库存（已下单未发货）、实际库存
- 下单时锁定库存（stock-=qty, locked+=qty），发货时扣减锁定库存（locked-=qty），取消时回滚（stock+=qty, locked-=qty）
- 所有库存变动生成库存流水，可追溯
- 高并发场景用 Redis 预扣库存 + 异步落库（一期日订单 500，数据库原子扣减足够）

#### 难点 3：支付回调幂等与验签

**问题**：微信/支付宝回调可能重复发送，伪造回调，回调金额与订单金额不一致。

**解决方案**：
- 验签：用平台公钥验证回调签名，验签失败直接拒绝
- 幂等：回调处理前先查订单状态，已支付则直接返回成功，不重复处理
- 金额校验：回调金额必须与订单金额一致，不一致记录异常并人工处理
- 用订单号做幂等键，加唯一索引
- 回调处理用数据库事务，要么全成功要么全回滚
- 主动查询：支付后前端轮询+后端定时主动查单（防止回调丢失）

#### 难点 4：低代码 Schema 设计与动态渲染（所见即所得）

**问题**：后台搭建器中拖拽的组件，H5 端必须完全一致地渲染；组件的内容配置和样式配置要能序列化存储并动态还原。

**解决方案**：
- 统一 Schema 格式：`{ pageStyle, components: [{ type, props, style, elementStyle }] }`
- 共享组件库：H5 端和后台画布用**同一套 React 组件**（放在 shared-components 包），保证渲染一致
- SchemaRenderer：遍历 components 数组，根据 type 从 componentMap 查找组件，注入 props/style/elementStyle 渲染
- 容器样式用外层 div 内联 style，元素样式用组件内部 style 属性或 CSS 变量
- 全局样式用 CSS 变量，商家改主题时 setProperty 全站生效
- 画布中渲染时加一层选中态包装（不影响组件本身）

#### 难点 5：SPU/SKU 数据模型

**问题**：商品规格（颜色/尺寸/容量）组合生成 SKU，规格可自定义，SKU 关联价格/库存/编码，模型设计错了后面全返工。

**解决方案**：
- SPU 表：商品基础信息（名称/分类/主图/详情/品牌）
- 规格表：规格定义（规格名，如"颜色"），规格值表（规格值，如"红色"）
- SPU 规格关联表：SPU 关联哪些规格
- SKU 表：每个规格组合对应一条 SKU（SPU_ID + 规格值组合 JSON + 价格 + 库存 + SKU编码 + 重量）
- 规格值组合用 JSON 字段存储，同时存一个唯一索引（SPU_ID + 规格值排序后的哈希）防重复
- 购物车/订单/库存全部按 SKU 维度操作

#### 难点 6：低代码组件的样式配置体系

**问题**：商家要能配置每个组件的样式，但配置项太多商家会懵，太少又不够用；动态样式不能用 Tailwind 类。

**解决方案**：
- 四层样式继承：全局 CSS 变量 → 页面级 → 组件级容器 → 元素级
- 组件级容器样式统一（所有组件都有：背景/边框/圆角/内边距/外边距/阴影/透明度），在属性面板"样式"Tab 统一配置
- 元素级样式由每个组件自己定义，只暴露最常用的 3-5 个配置项
- 预设样式：每个组件 2-3 套预设，一键套用，降低商家配置门槛
- 动态样式全部用内联 style 或 CSS 变量，**不用 Tailwind 动态类**（JIT 扫描不到）
- 元素级默认值用 CSS 变量，商家改全局主色时自动跟随

#### 难点 7：移动端性能优化

**问题**：H5 商城首屏加载慢、商品列表滚动卡顿、图片加载导致布局抖动。

**解决方案**：
- 首屏：路由懒加载 + 组件懒加载，首屏只加载首页必要组件
- 图片：WebP 格式 + CDN 按需裁剪 + 懒加载 + 固定宽高比占位防布局抖动
- 列表：商品列表超过 50 个用虚拟滚动（react-window），上拉加载分页
- 状态：React Query 缓存 API 结果，避免重复请求
- 构建：Vite 构建优化，代码分割，Tree Shaking，gzip/brotli 压缩
- 低代码页面：Schema 缓存到 Redis，组件用 React.memo 优化重渲染
- 动画：Framer Motion 用 transform/opacity（GPU 加速）

#### 难点 8：金额精度

**问题**：float 计算导致金额误差，财务对账对不上。

**解决方案**：
- 数据库用 `NUMERIC(12,2)`（精确到分）
- Python 用 `Decimal` 类型，所有金额计算用 Decimal
- 四舍五入用 `ROUND_HALF_UP`
- 优惠计算、运费、退款都用 Decimal，最后统一保留 2 位
- 订单金额 = 商品总价 + 运费 - 优惠，计算后与前端传的金额校验，不一致拒绝下单

#### 难点 9：后台 RBAC 权限

**问题**：多角色（超级管理员/运营/财务/仓管），不同角色看到不同菜单和按钮，数据权限不同。

**解决方案**：
- RBAC 模型：用户 → 角色 → 权限（菜单权限 + 按钮权限 + 数据权限）
- 菜单权限：前端路由表根据角色过滤，后端每个 API 校验角色
- 按钮权限：前端用自定义组件 `<Permission code="order:delete">` 控制按钮显示，后端 API 同样校验
- 数据权限：在查询时加数据范围过滤
- 操作日志：所有写操作记录（谁/什么时间/操作了什么/修改前后值）

#### 难点 10：订单超时自动取消

**问题**：用户下单后 30 分钟未支付，需要自动取消订单并回滚库存，不能漏也不能重复取消。

**解决方案**：
- 下单时往 Redis 有序集合（ZSET）写入 `{订单号: 过期时间戳}`
- 后台定时任务（每分钟）扫描 ZSET 中过期的订单，执行取消（回滚库存+释放优惠券+标记已取消）
- 取消操作加分布式锁（按订单号），防止定时任务和用户手动取消并发
- 取消后从 ZSET 删除
- 支付回调时先检查订单是否已取消，已取消则退款
- 一期可用 Celery/ARQ 的延迟任务，或简单的 APScheduler 定时扫描

### 8.2 官网端难点

#### 难点 11：低代码 Schema 在 Next.js SSG 中的渲染

**问题**：商城端的 SchemaRenderer 是 CSR 的（运行时从 API 拉 Schema 渲染），官网端需要 SSG（构建时生成静态 HTML），两者渲染时机不同。

**解决方案**：
- SchemaRenderer 组件本身是构建无关的（纯 React 组件，接收 schema prop 渲染），CSR 和 SSG 都能用
- SSG 时：Next.js `generateStaticParams` 获取所有页面 slug，`generateMetadata` 生成 SEO，页面组件在构建时通过 API（或直接读数据库）获取 Schema，传给 SchemaRenderer 渲染为静态 HTML
- ISR 时：后台修改页面后调用 Next.js revalidate API，触发该页面重新构建
- 客户端水合后：Schema 不变，直接复用静态 HTML，不需要重新拉取

#### 难点 12：共享组件库同时支持 Vite 和 Next.js

**问题**：shared-components 包同时被商城端（Vite）和官网端（Next.js）引用，需要确保组件不依赖特定构建 API。

**解决方案**：
- 共享组件只依赖 React 和通用库，不直接用 `import.meta.env`（Vite）或 `process.env`（Next.js），环境变量通过 props 传入
- 包用 TypeScript 编写，构建为 ESM + CJS 双格式（tsup 或 rollup），两个构建工具都能消费
- CSS（Tailwind）通过共享的 `shared-tokens` 包注入，两个端都引入同一个 CSS 文件
- 3D 组件单独打包（`@liteshop/3d-components`），只在官网端引用，不污染商城端包体积

#### 难点 13：3D 组件的低代码可配置性

**问题**：3D 场景参数多，全部暴露给商家配置会 overwhelm，且 3D 场景调试需要实时预览。

**解决方案**：
- 提供 5-6 个预设场景，商家选预设后只暴露 3-5 个关键参数（颜色、粒子密度、动画速度、鼠标交互开关）
- 后台画布中 3D 组件用真实 R3F Canvas 实时预览（和官网端一致），不是模拟图
- 高级参数（光照、相机、后期处理）折叠在"高级"Tab，默认不展示
- GLTF 模型上传后自动生成缩略图，支持在画布中拖拽旋转预览

#### 难点 14：滚动动画与低代码动态渲染的时机

**问题**：GSAP ScrollTrigger 需要在 DOM 渲染完成后计算元素位置，但低代码页面是动态渲染的（Schema 异步加载后才渲染组件），时机不对会导致 ScrollTrigger 计算位置错误。

**解决方案**：
- 页面 Schema 加载完成、所有组件挂载后，统一调用 `ScrollTrigger.refresh()` 重新计算所有触发点
- 图片加载完成后（`window.onload` 或图片 `onLoad`）再次 `ScrollTrigger.refresh()`（图片加载会改变页面高度）
- 用 `useLayoutEffect`（不是 useEffect）注册 ScrollTrigger，确保在浏览器绘制前完成
- 低代码页面切换时（客户端路由），先 `ScrollTrigger.killAll()` 清理旧页面的触发器，新页面渲染后再注册
- Lenis 初始化在 `useEffect` 中，确保 DOM 已挂载

#### 难点 15：SEO Meta 与低代码页面的结合

**问题**：每个低代码页面的 SEO 配置存在数据库 Schema 里，Next.js 需要在构建时（SSG）获取这些配置生成 Meta 标签。

**解决方案**：
- Next.js `generateMetadata({ params })` 中根据 slug 从 API/数据库获取页面 SEO 配置，返回 Metadata 对象
- 全局默认 SEO 存在 site_settings 表，页面级 SEO 覆盖全局默认
- 结构化数据（JSON-LD）在页面组件中根据页面类型注入
- OG Image 支持自动生成（用 `@vercel/og` 或后端 puppeteer 截图），商家也可上传自定义 OG 图

#### 难点 16：性能预算平衡（3D + GSAP + 低代码渲染）

**问题**：官网同时有 3D（600KB+）、GSAP（33KB）、Lenis（6KB）、低代码渲染，首屏性能容易超标。

**解决方案**：
- 首屏关键内容（Hero 文字+按钮+首屏图片）SSG 直出 HTML，不依赖 JS
- 3D 组件：`React.lazy` + IntersectionObserver，进入视口才加载；移动端直接降级为 2D，不加载 three.js
- GSAP/ScrollTrigger/Lenis：动态导入，只在有动画的页面加载
- 低代码 Schema：SSG 时已渲染为 HTML，客户端水合只做事件绑定
- 图片：Next.js Image 自动压缩+懒加载，Hero 图 preload
- 字体：next/font 自托管，`display: swap`
- 性能监控：用 `web-vitals` 库上报 Core Web Vitals，后台看板展示

#### 难点 17：联系表单的后端处理与反垃圾

**问题**：官网联系表单提交到后端，需要存储、通知商家、防垃圾提交（机器人刷表单）。

**解决方案**：
- 后端 FastAPI API 接收表单提交，校验（zod），存 form_submissions 表
- 通知：提交后发邮件给商家（SMTP）或发飞书/企微 webhook（可配置通知方式）
- 反垃圾：① 蜜罐字段（隐藏字段，机器人会填）② 提交频率限制（Redis 限流，同一 IP/邮箱 1 分钟 1 次）③ 可选 Turnstile/reCAPTCHA v3 ④ 内容检测（敏感词过滤）
- 后台可查看表单提交列表、标记已读/已处理、导出 Excel

---

## 九、坑点与风险

### 9.1 技术坑点

| # | 坑点 | 说明 | 规避方案 |
|---|---|---|---|
| 1 | **低代码动态样式用 Tailwind 类** | Tailwind v4 JIT 只扫描源码，商家运行时配置的 `bg-[#ff6b6b]` 不会被编译 | 动态样式用 CSS 变量或内联 style，静态页面才用 Tailwind 类 |
| 2 | **antd 与 Tailwind preflight 冲突** | Tailwind 的 preflight 会重置 button/input 等元素样式，导致 antd 组件样式异常 | `tailwind.config.js` 中 `corePlugins: { preflight: false }`，或用 CSS 层隔离 |
| 3 | **移动端滚动穿透** | 弹窗（SKU 抽屉）打开时，背景页面还能滚动 | 弹窗打开时给 body 加 `overflow:hidden` + `position:fixed`，记录 scrollTop，关闭时恢复 |
| 4 | **1px 边框高清屏发虚** | `border:1px` 在 2x/3x 屏上显得粗，`0.5px` 在部分安卓机不显示 | 用伪元素 `::after` + `transform:scaleY(0.5)` 实现真 1px，或统一用 1px 接受视觉差异 |
| 5 | **安全区域适配遗漏** | 底部固定栏在 iPhone 刘海屏被底部横条遮挡 | 封装 `<SafeAreaBottom>` 组件，所有底部固定栏加 `padding-bottom: env(safe-area-inset-bottom)` |
| 6 | **图片加载布局抖动（CLS）** | 商品图无固定高度，加载时把下方内容顶下去 | 所有商品图容器用 `aspect-[4/3]` 固定宽高比 + 灰色占位，图片 absolute 填充 |
| 7 | **支付回调重复通知** | 微信/支付宝会多次发送回调，重复处理导致重复发货 | 回调先查订单状态，已处理直接返回成功；用订单号做幂等键加唯一索引 |
| 8 | **库存并发超卖** | 先查库存再判断再扣减，并发下两个请求都查到有库存 | 用原子 SQL `UPDATE ... SET stock=stock-:qty WHERE stock>=:qty`，检查影响行数 |
| 9 | **金额用 float** | float 精度丢失，财务对账对不上 | 数据库 NUMERIC(12,2)，Python Decimal，统一 ROUND_HALF_UP |
| 10 | **订单超时取消遗漏** | 定时任务漏扫，订单一直待付款占库存 | Redis ZSET 存过期时间，每分钟扫描；支付时主动检查订单状态 |
| 11 | **数据库不备份** | 服务器故障/误操作导致数据丢失 | 每日 pg_dump 全量备份，存 OSS，保留 7 天，定期验证备份可恢复 |
| 12 | **低代码画布与端渲染不一致** | 画布中写了一套模拟组件，端是另一套，样式/行为不一致 | 共享组件库，画布和端用同一套组件，画布只加选中态包装层 |
| 13 | **大量内联样式性能差** | 低代码页面 20 个组件都有内联 style，React 重渲染时重新计算样式 | 全局样式用 CSS 变量，组件 style 用 useMemo 缓存，元素级只在配置了才注入 |
| 14 | **微信支付/支付宝资质不全** | 个人无法申请微信支付商户号，需要个体户/企业资质 | 提前注册个体工商户，申请微信支付商户号和支付宝商家号，配置回调域名 |
| 15 | **CORS 跨域** | 前后端分离部署，前端请求后端 API 被浏览器拦截 | FastAPI 配置 CORS 中间件，允许指定域名，生产环境不允许 `*` |
| 16 | **OSS 直传签名泄露** | 前端直传 OSS 用永久 AccessKey，泄露后被滥用 | 后端生成临时签名（STS Token 或 PostObject 签名），前端用临时凭证上传 |
| 17 | **短信验证码被刷** | 攻击者批量调用短信接口，产生大量短信费用 | 接口限流（Redis 计数器），图形验证码，IP 限流 |
| 18 | **商品详情图过长加载慢** | 详情页长图几 MB，加载慢 | 详情图切片上传，CDN 压缩，懒加载，限制单张图大小 |
| 19 | **SKU 规格组合爆炸** | 商品规格太多（5 色 × 10 尺寸 = 50 SKU），管理困难 | 限制规格数量（最多 3 个规格，每个规格最多 20 个值），SKU 批量编辑 |
| 20 | **退款与库存回滚不一致** | 退款成功但库存没回滚，或库存回滚了但退款失败 | 退款操作用数据库事务，退款接口调用+库存回滚+订单状态变更在一个事务内 |
| 21 | **GSAP 在 Next.js SSR 中 hydration 错误** | GSAP 操作 DOM，SSR 时没有 window，直接导入会报错 | 所有 GSAP 代码用 `dynamicImport(() => import('gsap'), { ssr: false })`，在 `useEffect` 中注册 |
| 22 | **R3F/Three.js 在 SSR 中 window 未定义** | Three.js 依赖 window/document，SSR 构建时报错 | 3D 组件全部 `React.lazy` + `ssr: false`，只在客户端渲染 |
| 23 | **Lenis 与 CSS position:sticky 冲突** | Lenis 用 transform 模拟滚动，会导致 sticky 元素不跟随 | Lenis 官方已修复 sticky 支持，需确保初始化在 sticky 元素渲染后 |
| 24 | **ScrollTrigger 与 React 严格模式双重挂载** | React 18 严格模式下组件挂载两次，ScrollTrigger 注册两次 | 开发环境关闭严格模式，或在 `useEffect` cleanup 中 `ScrollTrigger.kill()` |
| 25 | **3D 资源未 dispose 导致内存泄漏** | 低代码页面切换/组件卸载时，Three.js 资源未释放 | 组件卸载时遍历 scene dispose 所有资源；自定义 GLTF 模型需手动 traverse dispose |
| 26 | **移动端 3D 性能差/发热/耗电** | 移动端 GPU 弱，3D 场景持续渲染导致发热、FPS 骤降 | 移动端自动降级（检测 hardwareConcurrency/deviceMemory/UA），`frameloop="demand"`，dpr 限制 1.5 |
| 27 | **低代码页面 Schema 更新后 SSG 缓存未失效** | 后台改了页面内容，但 Next.js SSG 页面还是旧的 | 后台保存页面后调用 Next.js `revalidatePath('/slug')`；设置合理 revalidate 间隔兜底 |
| 28 | **自定义脚本注入 XSS 风险** | 商家在"自定义 HTML/JS"中注入恶意脚本 | 自定义脚本只允许超级管理员配置；白名单过滤；CSP 限制脚本来源 |
| 29 | **字体加载导致布局偏移（FOUT/FOIT）** | 自定义字体加载慢，文字先显示系统字体再切换 | 用 `next/font`（自动预加载、`display: swap`、`adjustFontFallback`）；字体自托管 |
| 30 | **GSAP 动画与 prefers-reduced-motion** | 用户系统开启"减少动画"时，动画仍在播放 | 全局检测 `matchMedia('(prefers-reduced-motion: reduce)')`，开启时禁用所有非必要动画 |
| 31 | **导航菜单锚点跳转与 Lenis 冲突** | 点击导航锚点，Lenis 平滑滚动和原生锚点跳转冲突 | 用 Lenis 的 `lenis.scrollTo('#anchor')` 方法跳转，不用原生 `href="#id"` |
| 32 | **GLTF 模型跨域/加载失败** | 模型文件存在 OSS，CORS 配置不当导致 Three.js 加载失败 | OSS 配置 CORS 允许来源；模型用 GLB（单文件）；加载失败时显示降级图 |
| 33 | **联系表单重复提交** | 用户双击提交按钮或网络慢时重复提交 | 提交后按钮禁用+loading；后端幂等校验（同一邮箱+同一内容 5 分钟内去重） |
| 34 | **Next.js 与 Vite 共享组件的 CSS 冲突** | 两个端的 Tailwind 配置/antd 主题不一致，共享组件样式错乱 | shared-tokens 包统一定义 Design Tokens，两个端都从 shared-tokens 引入 |

### 9.2 业务与合规风险

| # | 风险 | 说明 |
|---|---|---|
| 1 | **ICP 备案** | 商城和官网在国内运营必须 ICP 备案，备案期间网站不可访问 |
| 2 | **支付资质** | 微信支付/支付宝需要个体户或企业资质，个人无法申请 |
| 3 | **电商合规** | 需要用户协议、隐私政策、退换货政策，符合《电子商务法》《消费者权益保护法》 |
| 4 | **数据安全** | 用户手机号/地址/表单数据属于个人信息，需脱敏存储，符合《个人信息保护法》 |
| 5 | **发票** | 商家需要给消费者提供发票，系统需支持发票信息记录 |
| 6 | **经营范围** | 销售特定商品（食品/医疗器械/化妆品），需要相应经营资质 |
| 7 | **3D/动画版权** | 使用第三方 3D 模型、纹理、HDR 环境图需注意版权，商用需授权 |
| 8 | **字体版权** | 自定义字体（如方正、汉仪）商用需购买授权，免费字体（思源、Noto）可商用 |
| 9 | **SEO 内容合规** | 官网内容需真实，不得虚假宣传，符合《广告法》 |
| 10 | **表单数据隐私** | 联系表单收集的个人信息需在隐私政策中说明用途 |

### 9.3 项目管理风险

| # | 风险 | 说明 |
|---|---|---|
| 1 | **范围蔓延** | 低代码+ERP+商城+官网+3D 五个系统叠加，功能容易无限膨胀 | 严格按 MVP 范围执行，二期/三期功能不进入一期 |
| 2 | **低代码搭建器耗时超预期** | 拖拽编辑器+属性面板+组件库开发量大 | 一期只做 10 个商城组件，用 dnd-kit 减少自研拖拽成本；官网组件二期做 |
| 3 | **支付联调耗时** | 微信支付/支付宝沙箱环境配置复杂，回调调试耗时 | 提前申请商户号，先用沙箱联调，预留 1 周支付联调时间 |
| 4 | **3D 学习曲线陡** | React Three Fiber + Three.js 学习成本高，调试困难 | 3D 放三期，先做 2D 动画；3D 从简单预设场景（粒子/几何体）开始，不做复杂自定义模型 |
| 5 | **单人开发精力分散** | H5+官网+后台+后端+低代码五端并行，单人容易顾此失彼 | 按优先级串行开发：先后端核心 API → 再 H5 交易流程 → 再后台管理 → 再商城低代码 → 最后官网+3D |
| 6 | **Next.js 学习成本** | 开发者熟悉 Vite，Next.js App Router/RSC/SSG/ISR 有学习曲线 | 官网端二期才做，一期有时间学习；从简单 SSG 页面开始，逐步引入 ISR/RSC |

---

## 十、开发排期

### 10.1 一期（商城核心 + 商城低代码）— 约 15 周

| 阶段 | 周期 | 交付内容 |
|---|---|---|
| **第 1 阶段：基础架构** | 第 1-2 周 | Monorepo 初始化、shared-tokens、后端项目骨架（FastAPI+SQLAlchemy+PostgreSQL+Redis）、数据库设计、用户认证、OSS 上传签名、短信验证码 |
| **第 2 阶段：商品与库存** | 第 3-4 周 | 商品分类/SPU/SKU 管理（后台+API）、库存管理（实时库存/锁定库存/库存流水/原子扣减）、H5 商品分类/列表/详情页、SKU 选择弹窗、搜索 |
| **第 3 阶段：交易闭环** | 第 5-7 周 | 购物车（H5+Redis）、订单确认/提交、订单状态机、微信支付+支付宝（下单+回调+退款）、订单列表/详情、取消订单/确认收货、收货地址管理、订单超时自动取消 |
| **第 4 阶段：后台 ERP** | 第 8-10 周 | 数据看板、订单管理、售后管理、会员管理、系统设置、RBAC 权限、操作日志 |
| **第 5 阶段：商城低代码搭建器** | 第 11-13 周 | 三栏布局搭建器、dnd-kit 拖拽、10 个商城基础组件（shared-components）、属性面板（内容+样式）、预设样式、撤销重做、保存/自动保存、预览、页面管理、3 套模板、商城主题配置、H5 SchemaRenderer |
| **第 6 阶段：优化与上线** | 第 14-15 周 | 性能优化（首屏/图片/列表虚拟滚动）、兼容性测试、支付正式环境联调、部署（Docker Compose+Nginx+HTTPS）、数据备份、错误监控（Sentry）、文档编写 |

### 10.2 二期（官网低代码）— 约 6-8 周（在一期完成后）

| 阶段 | 周期 | 交付内容 |
|---|---|---|
| **官网端基础** | 第 1-2 周 | Next.js 项目初始化、App Router 结构、SSG/ISR 配置、官网 SchemaRenderer、Lenis+GSAP 集成、SEO 基础（generateMetadata/sitemap/robots） |
| **官网组件库** | 第 3-4 周 | 18 个官网组件（导航/Hero/内容展示/媒体交互）、每个组件动画配置、预设样式、响应式适配 |
| **后台搭建器扩展** | 第 5-6 周 | 画布尺寸切换、官网组件注册、动画 Tab、官网页面管理（路由/SEO）、导航菜单配置、全局网站设置、5 套官网模板、联系表单后台 |
| **后端扩展 + 优化上线** | 第 7-8 周 | 官网页面 CRUD、导航/设置存储、表单提交 API+反垃圾+通知、ISR webhook、性能优化（Core Web Vitals）、部署（Vercel/自托管+CDN）、测试上线 |

### 10.3 三期（3D + 高级功能）— 约 4-6 周（实验性）

| 阶段 | 周期 | 交付内容 |
|---|---|---|
| **3D 基础** | 第 1-2 周 | React Three Fiber + drei 集成、WebGPU 优先、按需渲染、3D 组件懒加载+移动端降级 |
| **3D 低代码组件** | 第 3-4 周 | Hero3DBackground（6 种预设）、Product3DViewer（GLTF 上传+热点标注）、后台 3D 配置面板+实时预览 |
| **高级动画 + 优化** | 第 5-6 周 | scrollytelling 时间线、3D 场景滚动驱动、性能优化、测试上线 |

---

## 十一、附录

### 11.1 术语表

| 术语 | 说明 |
|---|---|
| SPU | Standard Product Unit，标准化产品单元，如"iPhone 15" |
| SKU | Stock Keeping Unit，库存量单位，如"iPhone 15 黑色 128G" |
| Schema | 低代码页面的 JSON 描述，包含页面样式和组件列表 |
| RBAC | Role-Based Access Control，基于角色的访问控制 |
| OSS | Object Storage Service，对象存储服务 |
| SSG | Static Site Generation，静态站点生成（构建时生成 HTML） |
| ISR | Incremental Static Regeneration，增量静态再生（运行时重新生成特定页面） |
| SSR | Server-Side Rendering，服务端渲染 |
| CSR | Client-Side Rendering，客户端渲染 |
| RSC | React Server Components，React 服务端组件 |
| R3F | React Three Fiber，Three.js 的 React 渲染器 |
| LCP | Largest Contentful Paint，最大内容绘制（Core Web Vitals 指标） |
| INP | Interaction to Next Paint，交互到下一次绘制（Core Web Vitals 指标） |
| CLS | Cumulative Layout Shift，累积布局偏移（Core Web Vitals 指标） |
| JSON-LD | JSON for Linking Data，结构化数据格式，用于 SEO |
| OG | Open Graph，社交分享标签协议 |

### 11.2 核心数据表清单

**商城相关（一期）**：

| 表名 | 说明 |
|---|---|
| users | 用户表（H5 端消费者） |
| admins | 管理员表（后台） |
| roles | 角色表 |
| permissions | 权限表（菜单/按钮） |
| categories | 商品分类表 |
| products | 商品 SPU 表 |
| product_specs | 商品规格定义表 |
| product_spec_values | 规格值表 |
| skus | SKU 表（价格/库存/编码） |
| stock_logs | 库存流水表 |
| carts | 购物车表（或 Redis） |
| orders | 订单主表 |
| order_items | 订单商品明细表 |
| order_logs | 订单操作日志表 |
| payments | 支付记录表 |
| refunds | 退款单表 |
| after_sales | 售后单表 |
| addresses | 收货地址表 |
| favorites | 收藏表 |
| pages | 低代码页面表（商城页 + 官网页，含 Schema JSON） |
| page_templates | 页面模板表 |
| themes | 商城主题配置表 |
| suppliers | 供应商表（二期完善） |
| purchase_orders | 采购单表（二期完善） |
| settings | 系统设置表（键值对） |
| operation_logs | 操作日志表 |

**官网相关（二期新增）**：

| 表名 | 说明 |
|---|---|
| site_settings | 官网全局设置表（基础信息/SEO/主题/动画/脚本/域名） |
| nav_menus | 导航菜单表（顶部导航 + Footer） |
| form_submissions | 官网表单提交记录表 |
| form_notifications | 表单通知配置表 |

### 11.3 参考项目与技术资源

| 项目/资源 | 说明 | 参考点 |
|---|---|---|
| CRMEB | PHP 开源商城 | 低代码 DIY 装修、营销功能 |
| 萤火商城 2.0 | PHP 开源商城 | 轻量架构、H5+小程序 |
| Builder.io | React 可视化页面搭建 | 组件驱动低代码、Next.js 集成 |
| H5-Dooring | H5 页面可视化搭建平台 | 低代码编辑器架构 |
| v0.dev (Vercel) | AI 生成 React 页面 | shadcn/ui + Tailwind + Next.js 技术栈参考 |
| antd-mobile | React 移动端 UI 库 | H5 端组件 |
| dnd-kit | React 拖拽库 | 低代码拖拽排序 |
| FastAPI | Python 异步 Web 框架 | 后端 |
| Next.js App Router | React 全栈框架 | 官网 SSG/ISR/SEO |
| Lenis | 平滑滚动库 | 官网滚动体验 |
| GSAP + ScrollTrigger | 动画库 | 官网滚动动画 |
| React Three Fiber + drei | React 3D 库 | 官网 3D 效果 |
| shadcn/ui | 可定制 React 组件库 | 官网组件基础 |
| Tailwind CSS v4 | 原子化 CSS 框架 | 样式方案 |

---

---

# 附录 D：详细设计（v1.2 增补）

> 以下为 v1.2 评审后增补的详细设计。若与 v1.1 主体冲突，以附录 D 为准。

---

## D1. 数据模型详细设计

### D1.1 订单与售后状态机拆分（D-01）

#### D1.1.1 订单正向状态机

`orders.status` 只承担正向交易流转，共 5 个状态：

```
PENDING_PAYMENT ──支付成功──→ PAID ──发货──→ SHIPPED ──确认收货──→ COMPLETED
      │                                               ↑
      └──超时/手动取消──→ CANCELLED                    │
      └──支付前取消──→ CANCELLED                       │
```

| 状态 | 枚举值 | 含义 | 允许流转到 |
|---|---|---|---|
| 待付款 | `PENDING_PAYMENT` | 订单创建，等待支付 | PAID, CANCELLED |
| 已支付 | `PAID` | 支付成功，等待发货 | SHIPPED, CANCELLED（仅后台关闭） |
| 已发货 | `SHIPPED` | 已发货，等待收货 | COMPLETED |
| 已完成 | `COMPLETED` | 交易完成 | —（不可流转，售后走 after_sales） |
| 已取消 | `CANCELLED` | 订单取消，库存已回滚 | —（终态） |

**并发保护**：每次状态变更执行 `UPDATE orders SET status=:new WHERE id=:id AND status=:old`，检查影响行数为 1，否则抛 `ORDER_STATUS_CONFLICT`。

**冗余字段**：`orders.refund_status` 记录售后状态快照（仅用于 UI 展示，不参与状态机流转）：

| refund_status | 含义 |
|---|---|
| `NONE` | 无售后 |
| `APPLYING` | 有进行中售后申请 |
| `PARTIAL_REFUNDED` | 部分退款成功 |
| `REFUNDED` | 全额退款成功 |

#### D1.1.2 售后独立状态机

`after_sales.status` 独立流转，共 7 个状态：

```
PENDING_REVIEW ──同意──→ APPROVED ──买家退货──→ GOODS_RETURNED ──退款──→ REFUNDING ──退款成功──→ REFUNDED
      │                                                                                ↑
      └──拒绝──→ REJECTED                                               退款失败──→ REFUND_FAILED
                                                                                    │
                                                                      ┌─────────────┘
                                                                      ↓
                                                                   重试──→ REFUNDING
      └──买家超时未退货──→ CLOSED
      └──买家撤回──→ CLOSED
```

| 状态 | 枚举值 | 含义 | 允许流转到 |
|---|---|---|---|
| 待审核 | `PENDING_REVIEW` | 用户提交售后申请 | APPROVED, REJECTED, CLOSED |
| 已同意 | `APPROVED` | 后台同意，等待买家退货 | GOODS_RETURNED, CLOSED |
| 已拒绝 | `REJECTED` | 后台拒绝 | —（终态） |
| 已退货 | `GOODS_RETURNED` | 买家已寄回商品 | REFUNDING |
| 退款中 | `REFUNDING` | 调用支付渠道退款 | REFUNDED, REFUND_FAILED |
| 已退款 | `REFUNDED` | 退款成功 | —（终态） |
| 退款失败 | `REFUND_FAILED` | 退款接口失败 | REFUNDING（重试） |
| 已关闭 | `CLOSED` | 超时/撤回 | —（终态） |

**售后类型**：

| type | 含义 |
|---|---|
| `REFUND_ONLY` | 仅退款（未发货/已发货未收货） |
| `REFUND_AND_RETURN` | 退货退款（已收货） |
| `EXCHANGE` | 换货（二期） |

**与订单的关联**：
- 一个订单可以有多次售后（如部分退款），每次售后关联 `order_items` 子集
- 售后金额 ≤ 关联 order_items 实付总额
- 售后成功后库存回滚（`stock_logs.source_type = 'after_sale'`）

#### D1.1.3 orders 表结构修订

```sql
CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    order_no        VARCHAR(32) NOT NULL UNIQUE,          -- 订单号
    user_id         BIGINT NOT NULL REFERENCES users(id),
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING_PAYMENT',
    refund_status   VARCHAR(20) NOT NULL DEFAULT 'NONE',  -- v1.2 新增
    total_amount    INTEGER NOT NULL,                      -- 订单总金额（分）
    product_amount  INTEGER NOT NULL,                      -- 商品总金额（分）
    freight_amount  INTEGER NOT NULL DEFAULT 0,            -- 运费金额（分）
    discount_amount INTEGER NOT NULL DEFAULT 0,            -- 优惠金额（分）（一期预留）
    paid_amount     INTEGER,                               -- 实付金额（分）
    address_snapshot JSONB NOT NULL,                       -- 收货地址快照
    remark          TEXT,
    paid_at         TIMESTAMPTZ,
    shipped_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    cancel_reason   VARCHAR(200),
    expired_at      TIMESTAMPTZ,                           -- 支付超时时间
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_expired_at ON orders(expired_at) WHERE status = 'PENDING_PAYMENT';
```

#### D1.1.4 after_sales 表结构

```sql
CREATE TABLE after_sales (
    id              BIGSERIAL PRIMARY KEY,
    after_sale_no   VARCHAR(32) NOT NULL UNIQUE,          -- 售后单号
    order_id        BIGINT NOT NULL REFERENCES orders(id),
    user_id         BIGINT NOT NULL REFERENCES users(id),
    type            VARCHAR(20) NOT NULL,                 -- REFUND_ONLY / REFUND_AND_RETURN / EXCHANGE
    status          VARCHAR(20) NOT NULL DEFAULT 'PENDING_REVIEW',
    reason          TEXT NOT NULL,
    refund_amount   INTEGER NOT NULL,                      -- 退款金额（分）
    return_address  JSONB,                                 -- 退货地址（后台填写）
    return_tracking VARCHAR(100),                          -- 退货物流单号
    admin_remark    TEXT,                                  -- 后台备注
    reviewed_at     TIMESTAMPTZ,
    returned_at     TIMESTAMPTZ,
    refunded_at     TIMESTAMPTZ,
    closed_at       TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_after_sales_order_id ON after_sales(order_id);
CREATE INDEX idx_after_sales_user_id ON after_sales(user_id);
CREATE INDEX idx_after_sales_status ON after_sales(status);
```

#### D1.1.5 after_sale_items 关联表

```sql
CREATE TABLE after_sale_items (
    id              BIGSERIAL PRIMARY KEY,
    after_sale_id   BIGINT NOT NULL REFERENCES after_sales(id),
    order_item_id   BIGINT NOT NULL REFERENCES order_items(id),
    quantity        INTEGER NOT NULL,                      -- 退款数量
    refund_amount   INTEGER NOT NULL,                      -- 退款金额（分）
    UNIQUE(after_sale_id, order_item_id)
);
```

### D1.2 金额单位规约（D-02）

#### D1.2.1 全链路金额规约

| 层 | 存储/传输格式 | 示例 |
|---|---|---|
| PostgreSQL | `INTEGER`（分） | `1999` = ¥19.99 |
| Python 后端计算 | `Decimal`（元），序列化时转为 `int`（分） | `Decimal('19.99')` → API 输出 `1999` |
| API 请求/响应 | `integer`（分） | `"price": 1999` |
| TypeScript 前端 | `number`（分） | `const price = 1999` |
| 前端展示 | `formatPrice(1999)` → `"¥19.99"` | — |

#### D1.2.2 Pydantic 序列化层

```python
# backend/app/core/price.py
from decimal import Decimal, ROUND_HALF_UP
from pydantic import field_serializer, field_validator

CENTS_PER_YUAN = Decimal('100')

def yuan_to_cents(yuan: Decimal) -> int:
    """Decimal(元) → int(分)，四舍五入到分"""
    return int((yuan * CENTS_PER_YUAN).to_integral_value(rounding=ROUND_HALF_UP))

def cents_to_yuan(cents: int) -> Decimal:
    """int(分) → Decimal(元)"""
    return Decimal(cents) / CENTS_PER_YUAN

# Pydantic 模型中使用
class OrderResponse(BaseModel):
    total_amount: int  # 分

    @field_serializer('total_amount')
    def serialize_amount(self, v: int) -> int:
        return v  # 已经是分，直接输出

class OrderCreate(BaseModel):
    # 前端传入也是分
    total_amount: int
```

#### D1.2.3 TypeScript 前端工具函数

```typescript
// packages/shared-types/src/utils/price.ts

/** 分 → 展示字符串 */
export function formatPrice(cents: number, currency = '¥'): string {
  if (!Number.isFinite(cents)) return '-';
  const yuan = cents / 100;
  return `${currency}${yuan.toFixed(2)}`;
}

/** 分 → 元（用于计算） */
export function centsToYuan(cents: number): number {
  return cents / 100;
}

/** 元 → 分（用于提交） */
export function yuanToCents(yuan: number): number {
  return Math.round(yuan * 100);
}

/** 金额类型别名，语义化标注 */
export type Price = number; // 始终为分
```

#### D1.2.4 OpenAPI 字段约定

所有金额字段类型为 `integer`，字段名以 `_amount` / `_price` / `_fee` 结尾，注释标注"单位：分"：

```yaml
# OpenAPI 示例
Order:
  type: object
  properties:
    totalAmount:
      type: integer
      description: 订单总金额，单位：分
      example: 1999
```

### D1.3 购物车一致性设计（D-03）

#### D1.3.1 数据流

```
加购/改数量/删商品
       ↓
   写 Redis（主）
       ↓ 异步
   写 DB（备）
       ↓
  下单时：
  1. 从 DB 读 SKU 最新价格/库存
  2. 与请求中快照金额对比
  3. 不一致返回 PRICE_CHANGED
  4. 一致则创建 order + order_items（快照锁定）
```

#### D1.3.2 Redis 数据结构

```
# 用户购物车
Key:    cart:user:{user_id}
Value:  Hash
  Field: {sku_id}
  Value: JSON { quantity, added_at, stale }

# 游客购物车
Key:    cart:guest:{session_id}
Value:  Hash（同上）

# session_id → user_id 映射（登录合并用）
Key:    cart:session_map:{session_id}
Value:  {user_id}
TTL:    7d
```

#### D1.3.3 游客 → 登录合并流程

```
1. 用户登录成功
2. 读取 cart:guest:{session_id} 和 cart:user:{user_id}
3. 逐 SKU 合并：
   - 两边都有：数量取较大值（上限库存）
   - 仅一边有：直接合并
4. 写入 cart:user:{user_id}
5. 删除 cart:guest:{session_id}
6. 删除 cart:session_map:{session_id}
```

#### D1.3.4 SKU 变更同步

| 触发事件 | 购物车动作 |
|---|---|
| SKU 下架 | Celery 任务标记该 SKU 项 `stale=true, reason='off_shelf'` |
| SKU 改价 | 标记 `stale=true, reason='price_changed'` |
| SKU 库存变化 | 若库存 < 购物车数量，标记 `stale=true, reason='stock_insufficient'`，并调整数量 |
| 前端展示 | `stale=true` 的项标黄/红，提示"价格已变更/已下架/库存不足" |
| 结算校验 | 服务端取 SKU 最新数据，与请求快照对比 |

#### D1.3.5 DB 购物车表（异步落库）

```sql
CREATE TABLE cart_items (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users(id),
    sku_id      BIGINT NOT NULL REFERENCES skus(id),
    quantity    INTEGER NOT NULL DEFAULT 1,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, sku_id)
);

CREATE INDEX idx_cart_items_user_id ON cart_items(user_id);
```

#### D1.3.6 下单金额校验

```python
# backend/app/order/service.py
async def create_order(user_id: int, items: list[OrderItemInput]) -> Order:
    # 从 DB 读 SKU 最新数据
    sku_ids = [item.sku_id for item in items]
    skus = await sku_repo.get_by_ids(sku_ids)

    for item_input in items:
        sku = skus[item_input.sku_id]
        # 校验价格
        if sku.price_cents != item_input.price_cents:
            raise ApiError(
                code='PRICE_CHANGED',
                i18n_key='errors.price_changed',
                message=f'商品 {sku.name} 价格已变更，请重新确认',
                field='price_cents',
                details={'sku_id': sku.id, 'old': item_input.price_cents, 'new': sku.price_cents}
            )
        # 校验库存
        if sku.available_stock < item_input.quantity:
            raise ApiError(code='STOCK_INSUFFICIENT', ...)

    # 快照锁定：order_items 存下单时的价格/规格
    order = await order_repo.create(user_id, items, skus)
    # 清购物车对应项
    await cart_service.remove_items(user_id, sku_ids)
    return order
```

### D1.4 RBAC 权限模型（D-04）

#### D1.4.1 一期权限模型（菜单 + 按钮）

```sql
-- 管理员表
CREATE TABLE admins (
    id          BIGSERIAL PRIMARY KEY,
    username    VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name        VARCHAR(50),
    phone       VARCHAR(20),
    avatar      VARCHAR(500),
    is_super    BOOLEAN NOT NULL DEFAULT FALSE,  -- 超级管理员
    status      VARCHAR(10) NOT NULL DEFAULT 'ACTIVE',  -- ACTIVE / DISABLED
    last_login_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 角色表
CREATE TABLE roles (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE,     -- super_admin / operator / finance / warehouse
    label       VARCHAR(100) NOT NULL,           -- 超级管理员 / 运营 / 财务 / 仓管
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 管理员-角色关联
CREATE TABLE admin_roles (
    admin_id    BIGINT NOT NULL REFERENCES admins(id),
    role_id     BIGINT NOT NULL REFERENCES roles(id),
    PRIMARY KEY (admin_id, role_id)
);

-- 权限表
CREATE TABLE permissions (
    id          BIGSERIAL PRIMARY KEY,
    parent_id   BIGINT REFERENCES permissions(id),
    type        VARCHAR(10) NOT NULL,            -- MENU / BUTTON
    code        VARCHAR(100) NOT NULL UNIQUE,    -- e.g. 'product:delete', 'order:export'
    name        VARCHAR(100) NOT NULL,           -- e.g. '删除商品', '导出订单'
    path        VARCHAR(200),                     -- 前端路由路径（MENU 类型）
    icon        VARCHAR(50),
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 角色-权限关联
CREATE TABLE role_permissions (
    role_id       BIGINT NOT NULL REFERENCES roles(id),
    permission_id BIGINT NOT NULL REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);
```

#### D1.4.2 预置角色与权限

| 角色 | 权限范围 |
|---|---|
| 超级管理员 (`super_admin`) | 全部菜单 + 全部按钮 + 系统设置 + 支付配置 + 自定义脚本 |
| 运营 (`operator`) | 商品/订单/低代码/售后/会员菜单 + 对应操作按钮 |
| 财务 (`finance`) | 订单/售后/财务/数据看板菜单 + 导出 + 退款审核按钮 |
| 仓管 (`warehouse`) | 库存/订单(发货)/采购菜单 + 库存调整按钮 |

#### D1.4.3 前端权限组件

```tsx
// packages/admin-app/src/components/Permission.tsx
import { usePermission } from '@/hooks/usePermission';

export function Permission({ code, children, fallback = null }: {
  code: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  const { hasPermission } = usePermission();
  return hasPermission(code) ? <>{children}</> : <>{fallback}</>;
}

// 使用
<Permission code="order:delete">
  <Button danger>删除订单</Button>
</Permission>
```

#### D1.4.4 后端权限校验

```python
# backend/app/core/permission.py
from functools import wraps
from fastapi import HTTPException

def require_permission(code: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_admin=Depends(get_current_admin), **kwargs):
            if current_admin.is_super:
                return await func(*args, current_admin=current_admin, **kwargs)
            admin_permissions = await get_admin_permissions(current_admin.id)
            if code not in admin_permissions:
                raise HTTPException(status_code=403, detail='PERMISSION_DENIED')
            return await func(*args, current_admin=current_admin, **kwargs)
        return wrapper
    return decorator

# 使用
@router.delete('/orders/{order_id}')
@require_permission('order:delete')
async def delete_order(order_id: int, current_admin=Depends(get_current_admin)):
    ...
```

#### D1.4.5 二期数据权限预留

二期数据权限扩展方案（一期不实现，仅预留设计）：

```sql
-- 二期新增：角色数据范围
ALTER TABLE roles ADD COLUMN data_scope VARCHAR(20) DEFAULT 'ALL';
-- ALL: 全部数据
-- SELF: 仅自己创建的
-- DEPT: 本部门
-- DEPT_AND_SUB: 本部门及下属
-- CUSTOM: 自定义（role_data_scope_rules 表定义）
```

### D1.5 物流公司枚举与配置（D-05）

#### D1.5.1 shared-types 枚举

```typescript
// packages/shared-types/src/enums/logistics.ts

export const LogisticsCompanyCode = {
  SF: '顺丰速运',
  YTO: '圆通速递',
  ZTO: '中通快递',
  STO: '申通快递',
  YD: '韵达快递',
  JT: '极兔速递',
  EMS: '邮政EMS',
  DBL: '德邦快递',
  JD: '京东物流',
  FAST: '快捷速递',
  OTHER: '其他',
} as const;

export type LogisticsCompanyCodeType = keyof typeof LogisticsCompanyCode;
```

#### D1.5.2 后端配置表

```sql
-- 物流公司配置（后台可扩展）
CREATE TABLE logistics_companies (
    id          BIGSERIAL PRIMARY KEY,
    code        VARCHAR(20) NOT NULL UNIQUE,     -- SF/YTO/ZTO/...
    name        VARCHAR(50) NOT NULL,            -- 顺丰速运
    tracking_url_template VARCHAR(500),           -- https://www.sf-express.com/track?id={tracking_no}
    provider_code VARCHAR(20),                    -- 快递100/快递鸟编码（二期用）
    sort_order  INTEGER NOT NULL DEFAULT 0,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 一期预置数据
INSERT INTO logistics_companies (code, name, tracking_url_template, sort_order) VALUES
('SF', '顺丰速运', 'https://www.sf-express.com/track?id={tracking_no}', 1),
('YTO', '圆通速递', 'https://www.yto.net.cn/track?id={tracking_no}', 2),
('ZTO', '中通快递', 'https://www.zto.com/track?id={tracking_no}', 3),
('STO', '申通快递', 'https://www.sto.cn/track?id={tracking_no}', 4),
('YD', '韵达快递', 'https://www.yundaex.com/track?id={tracking_no}', 5),
('JT', '极兔速递', 'https://www.jtexpress.com.cn/track?id={tracking_no}', 6),
('EMS', '邮政EMS', 'https://www.ems.com.cn/track?id={tracking_no}', 7),
('DBL', '德邦快递', 'https://www.deppon.com/track?id={tracking_no}', 8),
('JD', '京东物流', 'https://www.jdl.com/track?id={tracking_no}', 9);
```

### D1.6 统一主题配置（D-29）

#### D1.6.1 site_themes 表

商城与官网共享同一主题表，通过 `scope` 字段区分：

```sql
CREATE TABLE site_themes (
    id          BIGSERIAL PRIMARY KEY,
    scope       VARCHAR(20) NOT NULL,             -- 'h5' / 'site' / 'global'
    key         VARCHAR(100) NOT NULL,             -- CSS 变量名
    value       VARCHAR(500) NOT NULL,             -- CSS 变量值
    label       VARCHAR(100),                      -- 后台展示名
    group_name  VARCHAR(50),                       -- 分组：color / spacing / border / typography
    sort_order  INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(scope, key)
);
```

#### D1.6.2 预置主题变量

| scope | key | 默认值 | label | group |
|---|---|---|---|---|
| global | --color-primary | #ff6b6b | 主色 | color |
| global | --color-success | #52c41a | 成功色 | color |
| global | --color-warning | #faad14 | 警告色 | color |
| global | --color-error | #ff4d4f | 错误色 | color |
| global | --color-text-primary | #1a1a1a | 主文字色 | color |
| global | --color-text-secondary | #666666 | 辅文字色 | color |
| global | --color-bg-primary | #ffffff | 主背景色 | color |
| global | --border-radius-base | 8px | 圆角基准 | border |
| global | --spacing-base | 16px | 间距基准 | spacing |
| h5 | --h5-tabbar-height | 50px | Tabbar 高度 | spacing |
| h5 | --h5-header-height | 44px | 顶部导航高度 | spacing |
| site | --site-nav-height | 72px | 导航栏高度 | spacing |
| site | --site-footer-bg | #1a1a1a | Footer 背景 | color |

#### D1.6.3 前端主题加载

```typescript
// H5 端启动时
async function loadTheme() {
  const res = await api.get('/api/settings/theme', { params: { scope: 'h5' } });
  const vars = res.data; // [{ key: '--color-primary', value: '#ff6b6b' }, ...]
  vars.forEach(({ key, value }) => {
    document.documentElement.style.setProperty(key, value);
  });
}

// 官网端同理，scope='site'
```

### D1.7 修订后的核心数据表清单

在 v1.1 附录 11.2 基础上，v1.2 新增/修改的表：

| 表名 | 说明 | 变更 |
|---|---|---|
| orders | 订单主表 | **修改**：status 枚举缩减为 5 个正向状态，新增 refund_status 字段，金额字段改为 INTEGER（分） |
| after_sales | 售后单表 | **修改**：status 枚举扩展为 7+1 个独立状态，新增 type 字段 |
| after_sale_items | 售后商品关联表 | **新增** |
| cart_items | 购物车 DB 表 | **新增**（Redis 为主，DB 异步落库） |
| logistics_companies | 物流公司配置表 | **新增** |
| site_themes | 统一主题配置表 | **新增** |
| freight_templates | 运费模板表 | **新增**（见 D6.5） |
| freight_template_items | 运费模板项表 | **新增**（见 D6.5） |
| notifications | 通知记录表 | **新增**（见 D6.1） |
| notification_templates | 通知模板表 | **新增**（见 D6.1） |
| reviews | 商品评价表 | **新增**（见 D6.2） |
| review_images | 评价图片表 | **新增**（见 D6.2） |

---

## D2. 接口契约详细设计

### D2.1 统一响应格式（D-02, D-08）

#### D2.1.1 成功响应

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... },
  "requestId": "req_abc123"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| code | integer | 0 表示成功，非 0 表示业务错误 |
| message | string | 默认中文消息，前端可基于 i18nKey 替换 |
| data | object/null | 业务数据，错误时为 null |
| requestId | string | 请求追踪 ID（UUID），与日志关联 |

#### D2.1.2 分页响应

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [...],
    "total": 100,
    "page": 1,
    "size": 20
  },
  "requestId": "req_abc123"
}
```

统一分页参数：
- `page`：从 1 开始
- `size`：默认 20，最大 100
- 排序：`sort=created_at:desc`（字段:方向，多字段用逗号分隔）

#### D2.1.3 错误响应（D-08 三层结构）

```json
{
  "code": 40004,
  "message": "商品价格已变更，请重新确认",
  "i18nKey": "errors.price_changed",
  "field": "price_cents",
  "details": {
    "skuId": 123,
    "oldPrice": 1999,
    "newPrice": 2099
  },
  "requestId": "req_abc123"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| code | integer | 是 | 业务错误码（见 D2.2） |
| message | string | 是 | 默认中文消息 |
| i18nKey | string | 否 | i18n key，前端有翻译时替换 message |
| field | string | 否 | 表单字段错误（用于表单校验高亮） |
| details | object | 否 | 错误详情（不含敏感信息） |
| requestId | string | 是 | 追踪 ID |

#### D2.1.4 HTTP 状态码映射

| HTTP | 场景 | code 范围 |
|---|---|---|
| 200 | 成功 | 0 |
| 400 | 参数错误/校验失败 | 10000-19999 |
| 401 | 未认证/Token 失效 | 40001 |
| 403 | 权限不足 | 40003 |
| 404 | 资源不存在 | 40400 |
| 409 | 状态冲突（如订单已支付） | 40900-40999 |
| 429 | 限流 | 42900 |
| 500 | 服务端错误 | 50000 |

### D2.2 错误码表（D-08）

#### D2.2.1 错误码命名规则

`{HTTP段}{模块}{序号}`，5 位数字：

| 段 | HTTP | 模块 |
|---|---|---|
| 1xxxx | 400 | 参数校验 |
| 2xxxx | 400 | 业务规则 |
| 4xxxx | 401/403/404 | 认证/权限/资源 |
| 429xx | 429 | 限流 |
| 5xxxx | 500 | 服务端 |

#### D2.2.2 核心错误码表

| code | i18nKey | 默认 message | HTTP | 模块 |
|---|---|---|---|---|
| 0 | common.success | ok | 200 | — |
| 10001 | common.param_invalid | 参数错误 | 400 | 通用 |
| 10002 | common.param_missing | 缺少必填参数 | 400 | 通用 |
| 10003 | common.param_type_error | 参数类型错误 | 400 | 通用 |
| 20001 | auth.invalid_credentials | 用户名或密码错误 | 400 | 认证 |
| 20002 | auth.sms_code_invalid | 验证码错误或已过期 | 400 | 认证 |
| 20003 | auth.sms_code_rate_limit | 验证码发送过于频繁 | 429 | 认证 |
| 20004 | auth.token_expired | Token 已过期 | 401 | 认证 |
| 20005 | auth.token_invalid | Token 无效 | 401 | 认证 |
| 20006 | auth.account_disabled | 账号已被禁用 | 403 | 认证 |
| 20101 | product.not_found | 商品不存在 | 404 | 商品 |
| 20102 | product.off_shelf | 商品已下架 | 400 | 商品 |
| 20103 | product.sku_not_found | SKU 不存在 | 404 | 商品 |
| 20201 | cart.empty | 购物车为空 | 400 | 购物车 |
| 20202 | cart.sku_stale | 购物车商品信息已变更 | 400 | 购物车 |
| 20203 | cart.quantity_exceed_stock | 购物车数量超出库存 | 400 | 购物车 |
| 20301 | order.not_found | 订单不存在 | 404 | 订单 |
| 20302 | order.status_conflict | 订单状态冲突 | 409 | 订单 |
| 20303 | order.price_changed | 商品价格已变更 | 400 | 订单 |
| 20304 | order.stock_insufficient | 库存不足 | 400 | 订单 |
| 20305 | order.expired | 订单已超时 | 400 | 订单 |
| 20306 | order.cannot_cancel | 订单当前状态不可取消 | 409 | 订单 |
| 20307 | order.cannot_pay | 订单当前状态不可支付 | 409 | 订单 |
| 20401 | stock.insufficient | 库存不足 | 400 | 库存 |
| 20402 | stock.lock_failed | 库存锁定失败 | 409 | 库存 |
| 20501 | payment.order_paid | 订单已支付 | 409 | 支付 |
| 20502 | payment.amount_mismatch | 支付金额不匹配 | 400 | 支付 |
| 20503 | payment.signature_invalid | 支付签名验证失败 | 400 | 支付 |
| 20504 | payment.refund_failed | 退款失败 | 500 | 支付 |
| 20601 | after_sale.not_found | 售后单不存在 | 404 | 售后 |
| 20602 | after_sale.status_conflict | 售后状态冲突 | 409 | 售后 |
| 20603 | after_sale.amount_exceed | 退款金额超出订单金额 | 400 | 售后 |
| 20701 | upload.file_type_invalid | 文件类型不允许 | 400 | 上传 |
| 20702 | upload.file_too_large | 文件大小超限 | 400 | 上传 |
| 20703 | upload.signature_invalid | 上传签名无效 | 400 | 上传 |
| 20801 | page.schema_invalid | 页面 Schema 格式错误 | 400 | 低代码 |
| 20802 | page.component_not_found | 组件类型不存在 | 400 | 低代码 |
| 40001 | auth.unauthorized | 未登录 | 401 | 认证 |
| 40003 | auth.permission_denied | 权限不足 | 403 | 权限 |
| 40400 | common.not_found | 资源不存在 | 404 | 通用 |
| 40900 | common.conflict | 资源状态冲突 | 409 | 通用 |
| 42900 | common.rate_limited | 请求过于频繁，请稍后重试 | 429 | 限流 |
| 50000 | common.server_error | 服务器内部错误 | 500 | 通用 |
| 50001 | common.service_unavailable | 服务暂时不可用 | 503 | 通用 |
