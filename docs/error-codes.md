# LiteShop 错误码表 v1

所有错误响应统一包含 `code`、`i18nKey`、`message`、`requestId`；字段错误可选 `field` 和 `details`。HTTP 状态码与业务码同时返回。金额字段一律为整数分。

| code | i18nKey | 默认 message | HTTP | 模块 |
|---:|---|---|---:|---|
| 0 | common.ok | 成功 | 200 | 通用 |
| 40001 | common.invalid_request | 请求参数错误 | 400 | 通用 |
| 40101 | auth.unauthorized | 未登录或令牌无效 | 401 | 认证 |
| 40102 | auth.token_expired | Token 已过期 | 401 | 认证 |
| 40301 | common.forbidden | 无权执行此操作 | 403 | 通用 |
| 40401 | common.not_found | 资源不存在 | 404 | 通用 |
| 40901 | order.invalid_transition | 订单状态不允许此操作 | 409 | 订单 |
| 40902 | inventory.insufficient | 库存不足 | 409 | 库存 |
| 40903 | order.price_changed | 商品价格已变更，请重新确认 | 409 | 订单 |
| 40904 | payment.amount_mismatch | 支付金额校验失败 | 409 | 支付 |
| 40905 | payment.refund_invalid | 退款金额或支付状态不允许退款 | 409 | 支付 |
| 40906 | payment.duplicate_callback | 重复支付回调，已忽略 | 200 | 支付 |
| 42201 | common.validation_error | 数据校验失败 | 422 | 通用 |
| 42901 | common.request_in_progress | 请求正在处理，请稍后再试 | 429 | 通用 |
| 42902 | common.duplicate_request | 重复请求，已为您返回原结果 | 200 | 通用 |
| 50001 | common.internal_error | 服务暂时不可用 | 500 | 通用 |

## 幂等约定

- 所有 POST/PUT/DELETE 写接口必须携带 `X-Request-Id` UUID。
- 后端以 `(userId, requestId, actionType)` 写入 Redis 5 分钟，并以 `client_request_id` 唯一索引兜底。
- 重复请求返回原资源和 `42902` 或业务成功响应，不得重复创建订单、支付流水或库存流水。
