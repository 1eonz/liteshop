# 验证命令

以下命令对应当前 package.json 与 backend 配置。测试结果记在 [当前交接](交接文档-当前阶段.md)，不把历史数字当作当次验收。

## H5 / Admin

在仓库根目录执行；Admin 将路径改为 `packages/admin-app`。每条必须单独检查退出码。

```powershell
pnpm --dir packages/h5-app typecheck
pnpm --dir packages/h5-app lint
pnpm --dir packages/h5-app test
pnpm --dir packages/h5-app build
```

开发预览：`pnpm --dir packages/h5-app exec vite --host 127.0.0.1 --port 4173 --strictPort`。不要在 `pnpm dev` 后额外插入 `--` 导致参数未传给 Vite。

## Site / 共享包

```powershell
pnpm --dir packages/site-app build
pnpm --dir packages/site-app typecheck
pnpm --dir packages/site-app lint
pnpm --dir packages/site-app test
pnpm --dir packages/shared-types build
pnpm --dir packages/shared-types test
pnpm --dir packages/shared-components build
pnpm --dir packages/shared-components test
pnpm --dir packages/shared-3d-components test
```

Site 先构建以生成 `.next/types`。需要预览生产构建时运行 `pnpm --dir packages/site-app exec next start --hostname 127.0.0.1 --port 4175`，该包没有 `start` 脚本。

## 后端

使用已安装 `backend/requirements.txt` 的 Python 3.12 环境，从 `backend` 目录运行：

```powershell
python -m ruff check .
python -m mypy .
python -m pytest -q --cov=app --cov-report=term-missing
```

真实集成只指向本地/隔离测试库；需要 PostgreSQL/Redis 和测试夹具。默认测试不会替代该检查。

```powershell
$env:LITESHOP_RUN_INTEGRATION = '1'
$env:LITESHOP_USE_DATABASE = 'true'
python -m pytest -q integration_tests/test_postgres_redis.py integration_tests/test_real_http_api.py
```

迁移回退只能在明确创建的临时库执行，不把 `downgrade` 列为普通开发库的常规验证。

## 端到端

```powershell
pnpm --dir tests/e2e test
```

配置会启动 H5/Admin/Site 本地服务。真实 API 用例需要本地后端，可用 `E2E_API_BASE` 配置地址；端口冲突用 `E2E_H5_PORT`、`E2E_ADMIN_PORT`、`E2E_SITE_PORT`。报告必须区分通过、失败和跳过，不能把未启动后端的跳过算作通过。

## 全仓与交付检查

```powershell
pnpm typecheck
pnpm lint
pnpm test
pnpm build
python scripts/check_enum_sync.py
git diff --check
```

只改一个包时先执行受影响包的命令。UI 另做实际浏览器的视口、键盘、加载/失败、禁用、长文案及 reduced-motion 检查。构建输出中的入口 gzip 和首屏实际依赖图用于体积判断，不能把所有 lazy chunk 总和叫作“首屏体积”。

当前仓库未配置 `test:a11y`、`test:e2e:vite`、`test:e2e:nextjs` 脚本，不再列出不存在的命令。完整 a11y 自动验收仍是待补项。
