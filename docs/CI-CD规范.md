# LiteShop CI/CD 规范

> 本文件定义 LiteShop 项目的持续集成/持续部署流水线、质量门禁、安全扫描规范。
> 主 Agent 在 plan-01 阶段生成 `.github/workflows/` 下两个 workflow 文件（ci.yml + deploy.yml），1a 期所有 PR 必须通过 CI 才能合并。

---

> **分期适用（唯一事实源：AGENTS.md §十四 运维能力分期适用矩阵）**
>
> | 能力 | 1a 期（必须） | 1b 期 | 增长期（触发：日订单 > 2000） |
> |---|---|---|---|
> | CI | lint/测试/类型/构建/安全扫描门禁（每 PR 必跑） | 同 1a | 同 1a |
> | 发布 | 脚本部署（scripts/deploy.ps1）+ tag 回滚 + 备份后发布 | 同 1a | 4 阶段灰度（1% → 10% → 50% → 100%） |
>
> 本文部署流水线中的多阶段灰度为**增长期参考**；1a 期发布 = 构建产物 + 备份 + 脚本部署 + 健康检查 + 失败 tag 回滚。

---

## 一、流水线总览

```
开发者推送 feat/plan-* 分支
  ↓
[CI 流水线]（每个 PR 必跑，~5 分钟）
  ├─ 代码质量（lint + format check）
  ├─ 单元测试 + 覆盖率门禁
  ├─ 类型检查
  ├─ 构建（所有端）
  ├─ 安全扫描（SAST + SCA）
  ├─ OpenAPI 契约校验
  └─ 包体积门禁
  ↓ 全绿才允许合并
[人工 review + 合并到 main]
  ↓
[部署流水线]（打 tag 触发，~10 分钟）
  ├─ 构建生产镜像
  ├─ 推送到镜像仓库
  ├─ 灰度部署（1% → 10% → 50% → 100%）
  ├─ 健康检查
  └─ 失败自动回滚
```

---

## 二、CI 流水线定义（.github/workflows/ci.yml）

### 2.1 触发条件

```yaml
on:
  pull_request:
    branches: [main, feat/**]
  push:
    branches: [main]
```

### 2.2 Job 结构

| Job | 运行条件 | 跑什么 |
|---|---|---|
| `lint` | 所有 PR | ruff + eslint + prettier --check |
| `backend-test` | 所有 PR | pytest + mypy + 覆盖率门禁 ≥ 80% |
| `frontend-test` | 所有 PR | h5-app/admin-app/shared-* vitest + tsc + 覆盖率 ≥ 70% |
| `build` | 所有 PR | 所有端 pnpm build |
| `security-scan` | 所有 PR | bandit + pip-audit + pnpm audit + trufflehog |
| `contract-check` | 所有 PR | Spectral lint OpenAPI + 枚举同步检查 |
| `bundle-size` | 所有 PR | H5 首屏 gzip ≤ 200KB，Admin ≤ 500KB |
| `e2e` | 仅 feat/plan-* 合并到 main 时 | Playwright 冒烟 |

### 2.3 质量门禁阈值

| 指标 | 阈值 | 失败处理 |
|---|---|---|
| backend 覆盖率 | ≥ 80%（支付/库存/订单模块 ≥ 95%） | CI fail |
| frontend 覆盖率 | ≥ 70% | CI fail |
| H5 首屏 JS gzip | ≤ 200KB | CI fail |
| Admin 总 JS gzip | ≤ 500KB | CI fail |
| ruff/eslint 错误 | 0 | CI fail |
| mypy 错误 | 0 | CI fail |
| 依赖高危漏洞 | 0（pip-audit + pnpm audit） | CI fail |
| OpenAPI 校验 | 0 error | CI fail |
| 枚举同步 | 0 差异 | CI fail |

---

## 三、部署流水线定义（.github/workflows/deploy.yml）

### 3.1 触发条件

```yaml
on:
  push:
    tags: ['v*.*.*']
  workflow_dispatch:
    inputs:
      env:
        description: '部署环境'
        required: true
        type: choice
        options: [staging, production]
```

### 3.2 部署阶段

1. **构建镜像**：`docker build -t liteshop-backend:${tag} ./backend`
2. **推送镜像仓库**：阿里云 ACR / Docker Hub
3. **灰度部署**（生产环境）：
   - 1% 流量切到新版本，观察 5 分钟（错误率/延迟/告警）
   - 10% → 观察 10 分钟
   - 50% → 观察 10 分钟
   - 100% → 完成
4. **健康检查**：`/api/v1/health` 连续 3 次返回 200
5. **失败自动回滚**：任一阶段错误率 > 1% 或健康检查失败 → 回滚到上一版本

### 3.3 部署前置检查清单

- [ ] CI 流水线全绿
- [ ] 数据库迁移已通过 staging 验证（含回滚测试）
- [ ] `.env.production` 已注入（CORS 收紧/COOKIE_SECURE=true/加密密钥已生成）
- [ ] 支付回调 URL 已切换为生产域名
- [ ] 回滚预案已准备（上一版本镜像 tag + Alembic downgrade 命令）
- [ ] 监控告警已配置（Sentry release tag + Prometheus 告警规则）

---

## 四、安全扫描规范

### 4.1 SAST（静态应用安全测试）

| 工具 | 语言 | 跑什么 | 失败阈值 |
|---|---|---|---|
| bandit | Python | 安全规则扫描（SQL 注入/弱加密/硬编码密钥） | high 级别 > 0 失败 |
| eslint-plugin-security | JS/TS | 禁用 eval/innerHTML/正则 DoS | error 级别 > 0 失败 |

### 4.2 SCA（软件成分分析，依赖漏洞）

| 工具 | 生态 | 命令 | 失败阈值 |
|---|---|---|---|
| pip-audit | Python | `pip-audit -r requirements.txt` | high/critical > 0 失败 |
| pnpm audit | Node | `pnpm audit --audit-level=high` | high/critical > 0 失败 |

### 4.3 密钥扫描

| 工具 | 跑什么 | 失败阈值 |
|---|---|---|
| trufflehog | 扫描 git 历史是否有泄露的 API key/JWT/私钥 | 任何命中即 fail |

### 4.4 镜像扫描（生产部署前）

| 工具 | 跑什么 | 失败阈值 |
|---|---|---|
| trivy | `trivy image liteshop-backend:${tag}` | high/critical > 0 失败 |
| hadolint | `hadolint backend/Dockerfile` | error 级别 > 0 失败 |

---

## 五、版本号与 Tag 规约

### 5.1 语义化版本

```
v{MAJOR}.{MINOR}.{PATCH}
```

- MAJOR：破坏性变更（API 不兼容/数据模型重构）
- MINOR：新功能（向后兼容）
- PATCH：bug 修复
- 预发布：`v1.0.0-rc.1` / `v1.0.0-beta.2`

### 5.2 Tag 规约

```bash
# 1a 期首个发布
git tag v1.0.0 -m "1a 期正式发布"
git push origin v1.0.0

# 紧急修复
git tag v1.0.1 -m "hotfix: 支付回调幂等修复"
```

---

## 六、Hotfix 紧急通道

### 6.1 适用场景

P0 级线上故障（支付失败/库存超卖/全站 500），需在 1 小时内修复上线。

### 6.2 流程

1. 从 `main` 拉出 `hotfix/{issue-id}` 分支
2. 最小改动修复，只改必要文件
3. 跑核心验证（backend pytest + 支付/库存模块单测 + e2e 冒烟）
4. PR review 由 1 人即可（正常 2 人）
5. 合并后打 `v{当前版本}-hotfix.{N}` tag
6. 走简化部署流水线（跳过灰度，直接 100%）
7. 事后补 postmortem（24 小时内）

### 6.3 Hotfix 限制

- 禁止重构
- 禁止依赖升级
- 禁止数据库破坏性迁移（只能加可空字段/加索引）
- 限制改动文件数 ≤ 5

---

## 七、环境隔离规约

| 维度 | development | staging | production |
|---|---|---|---|
| 数据库 | 本地 PG | 独立 RDS | 独立 RDS（读写分离） |
| Redis | 本地 | 独立实例 | 独立实例（哨兵） |
| 密钥 | 开发默认值 | 独立注入 | 强随机文件密钥（FIELD_ENCRYPTION_KEY，权限 600）；KMS 为增长期（PRD D5.1） |
| CORS | localhost | staging 域名 | 真实域名收紧 |
| 支付 | 沙箱 | 沙箱 | 正式 |
| Sentry 环境 | development | staging | production |
| 数据 | 假数据 | 脱敏后的生产快照 | 真实数据 |

**红线**：
- 永不从 production 复制真实数据到 development/staging
- 永不在 staging 跑正式支付
- 永不共享密钥跨环境

---

## 八、CI 依赖安装优化

```yaml
# 缓存策略
- uses: actions/setup-node@v4
  with:
    node-version: 22
    cache: 'pnpm'
- uses: actions/setup-python@v5
  with:
    python-version: 3.12
    cache: 'pip'
```

---

## 九、与 PRD/AGENTS.md 的对应

| 本文件章节 | 对应文档 |
|---|---|
| CI 流水线 | AGENTS.md §5 验证要求、docs/verify-commands.md |
| 质量门禁 | PRD E15 验收清单 |
| 安全扫描 | AGENTS.md §6 安全红线、PRD D5 安全合规 |
| 部署灰度 | PRD D7.4 蓝绿部署 |
| 环境隔离 | AGENTS.md §8 人工介入红线（永不连生产） |
| Hotfix | PRD D8.1 阶段规划（hotfix 不在 1a 排期内，但流程需预留） |

---

## 十、project-radar 集成

project-radar skill 在风险检测时自动检查：
- 是否有 `.github/workflows/` 目录 → 无则 🔴 高风险（CI 缺失）
- 是否有依赖锁文件（pnpm-lock.yaml / requirements.txt 锁定版本） → 无则 🟡
- 是否有 `.gitignore` 排除 `.env.*`（除 .env.example） → 否则 🔴 密钥泄露风险
- 是否有 prettier/eslint/ruff/mypy 配置文件 → 无则 🟡

---

**文件结束**

> CI/CD 是 LiteShop 从"能跑"到"能上线"的关键。1a 期必须完整落地 CI 流水线 + 质量门禁 + 安全扫描，部署流水线可在 1b 期完善灰度。
> Hotfix 通道虽不在 1a 排期内，但分支策略和流程需提前预留，避免线上故障时手忙脚乱。
