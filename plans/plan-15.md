# Plan 15：认证、验证码、Token 撤销与可信 IP

> PRD 章节：D2.1+E3.4+E11.5+E16.6

## 任务清单
- [x] Redis GETDEL/Lua 原子消费短信验证码。
- [x] 首次并发手机号登录使用 upsert 或唯一冲突恢复。
- [x] refresh token 携带 jti/session，刷新时轮换并撤销旧 token。
- [x] 登出撤销当前 refresh token，旧 token 重放返回统一错误。
- [x] 仅在配置可信代理网段时读取 X-Forwarded-For。
- [x] 登录、短信和审计均使用可信 IP。
- [x] 增加验证码并发、Token 重放、登出和伪造 IP 测试。
- [ ] auth OpenAPI、错误码和安全文档在契约同步阶段统一复核。

## 验收标准
- [x] 同一验证码最多一个并发请求成功。
- [x] refresh 轮换后旧 token 立即失效。

## 验收记录

- `ruff check .`：通过。
- `mypy .`：通过，94 个源文件。
- `pytest -q`：33 passed。
- 主 Agent 抽查 Lua 原子脚本、Token 轮换和可信代理解析：通过。
