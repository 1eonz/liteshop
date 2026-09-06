"""购物车服务：数据库模式使用 Redis，测试模式使用进程内后备存储。"""

import asyncio
import builtins
import json
from dataclasses import dataclass
from typing import cast

from redis.exceptions import RedisError

from ..core.config import settings
from ..core.redis import redis_client


class CartError(ValueError):
    """购物车业务错误。"""


@dataclass(frozen=True)
class CartLine:
    """购物车中的一行 SKU。"""

    sku_id: int
    quantity: int
    price_cents: int


class CartService:
    """封装 Redis Hash 和进程内测试后备实现。"""

    def __init__(self) -> None:
        self._memory: dict[str, dict[int, CartLine]] = {}
        self._memory_lock = asyncio.Lock()

    max_sku_quantity = 999
    max_total_quantity = 99

    @staticmethod
    def _key(user_id: str) -> str:
        return f"cart:{user_id}"

    @staticmethod
    def _encode(line: CartLine) -> str:
        return json.dumps({"skuId": line.sku_id, "quantity": line.quantity, "priceCents": line.price_cents})

    @staticmethod
    def _decode(raw: str) -> CartLine:
        value = cast(dict[str, object], json.loads(raw))
        return CartLine(
            cast(int, value["skuId"]),
            cast(int, value["quantity"]),
            cast(int, value["priceCents"]),
        )

    async def list(self, user_id: str, *, use_database: bool) -> list[CartLine]:
        """按加入顺序读取购物车。"""
        if not use_database:
            return list(self._memory.get(user_id, {}).values())
        try:
            values = await redis_client.hvals(self._key(user_id))
        except RedisError as exc:
            raise CartError("购物车服务暂不可用") from exc
        return [self._decode(value.decode() if isinstance(value, bytes) else value) for value in values]

    async def add(self, user_id: str, line: CartLine, *, use_database: bool, request_id: str | None = None) -> CartLine:
        """添加 SKU；已存在项累加数量。"""
        if line.quantity <= 0:
            raise CartError("数量必须大于零")
        if not use_database:
            async with self._memory_lock:
                bucket = self._memory.setdefault(user_id, {})
                current = bucket.get(line.sku_id)
                next_quantity = (current.quantity if current else 0) + line.quantity
                total_quantity = sum(item.quantity for item in bucket.values()) - (current.quantity if current else 0)
                if next_quantity > self.max_sku_quantity or total_quantity + next_quantity > self.max_total_quantity:
                    raise CartError("购物车数量已达到上限")
                next_line = CartLine(
                    line.sku_id,
                    next_quantity,
                    line.price_cents,
                )
                bucket[line.sku_id] = next_line
                return next_line
        key = self._key(user_id)
        try:
            idempotency_key = f"cart:request:{user_id}:{request_id}" if request_id else ""
            script = """
local idem = ARGV[4]
if idem ~= '' then
  local cached = redis.call('GET', idem)
  if cached then return cached end
end
local raw = redis.call('HGET', KEYS[1], ARGV[1])
local current = 0
if raw then
  current = cjson.decode(raw).quantity
end
local next_quantity = current + tonumber(ARGV[2])
if next_quantity > 999 then
  return redis.error_reply('购物车单 SKU 数量不能超过 999')
end
local total = 0
local entries = redis.call('HVALS', KEYS[1])
for _, entry in ipairs(entries) do
  total = total + cjson.decode(entry).quantity
end
if total - current + next_quantity > 99 then
  return redis.error_reply('购物车总件数不能超过 99')
end
local value = cjson.encode({skuId=tonumber(ARGV[1]), quantity=next_quantity, priceCents=tonumber(ARGV[3])})
redis.call('HSET', KEYS[1], ARGV[1], value)
if idem ~= '' then redis.call('SET', idem, value, 'EX', ARGV[5]) end
return value
"""
            raw = await redis_client.eval(
                script,
                1,
                key,
                line.sku_id,
                line.quantity,
                line.price_cents,
                idempotency_key,
                settings.idempotency_ttl_seconds,
            )
            text = raw.decode() if isinstance(raw, bytes) else str(raw)
            return self._decode(text)
        except RedisError as exc:
            raise CartError("购物车服务暂不可用") from exc

    async def update(
        self, user_id: str, line: CartLine, *, use_database: bool, request_id: str | None = None
    ) -> CartLine:
        """覆盖 SKU 数量。"""
        if line.quantity <= 0:
            raise CartError("数量必须大于零")
        if not use_database:
            bucket = self._memory.setdefault(user_id, {})
            if line.sku_id not in bucket:
                raise CartError("购物车项不存在")
            other_total = sum(item.quantity for sku_id, item in bucket.items() if sku_id != line.sku_id)
            if line.quantity > self.max_sku_quantity or other_total + line.quantity > self.max_total_quantity:
                raise CartError("购物车数量已达到上限")
            bucket[line.sku_id] = line
            return line
        try:
            key = self._key(user_id)
            idempotency_key = f"cart:request:{user_id}:{request_id}" if request_id else ""
            if idempotency_key:
                cached = await redis_client.get(idempotency_key)
                if cached:
                    return self._decode(cached.decode() if isinstance(cached, bytes) else cached)
            if not await redis_client.hexists(key, str(line.sku_id)):
                raise CartError("购物车项不存在")
            values = await redis_client.hvals(key)
            other_total = sum(
                self._decode(value.decode() if isinstance(value, bytes) else value).quantity
                for value in values
                if self._decode(value.decode() if isinstance(value, bytes) else value).sku_id != line.sku_id
            )
            if line.quantity > self.max_sku_quantity or other_total + line.quantity > self.max_total_quantity:
                raise CartError("购物车数量已达到上限")
            await redis_client.hset(key, str(line.sku_id), self._encode(line))
            if idempotency_key:
                await redis_client.set(idempotency_key, self._encode(line), ex=settings.idempotency_ttl_seconds)
            return line
        except RedisError as exc:
            raise CartError("购物车服务暂不可用") from exc

    async def remove(self, user_id: str, sku_id: int, *, use_database: bool, request_id: str | None = None) -> None:
        """删除指定 SKU。"""
        if not use_database:
            self._memory.setdefault(user_id, {}).pop(sku_id, None)
            return
        try:
            idempotency_key = f"cart:request:{user_id}:{request_id}" if request_id else ""
            if idempotency_key and await redis_client.get(idempotency_key):
                return
            await redis_client.hdel(self._key(user_id), str(sku_id))
            if idempotency_key:
                await redis_client.set(idempotency_key, "1", ex=settings.idempotency_ttl_seconds)
        except RedisError as exc:
            raise CartError("购物车服务暂不可用") from exc

    async def clear_items(self, user_id: str, sku_ids: builtins.list[int], *, use_database: bool) -> None:
        """订单成功后删除已经结算的服务端购物车项。"""
        if not sku_ids:
            return
        if not use_database:
            async with self._memory_lock:
                bucket = self._memory.setdefault(user_id, {})
                for sku_id in sku_ids:
                    bucket.pop(sku_id, None)
            return
        try:
            await redis_client.hdel(self._key(user_id), *(str(sku_id) for sku_id in sku_ids))
        except RedisError as exc:
            raise CartError("购物车服务暂不可用") from exc


cart_service = CartService()
