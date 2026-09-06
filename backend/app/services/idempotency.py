"""写接口 Redis + DB 双层幂等编排。"""

import json
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import cast

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.database import transaction
from ..core.idempotency import idempotency_store, make_idempotency_key
from ..repositories.idempotency import IdempotencyRepository


class IdempotencyInProgress(RuntimeError):
    """同一个请求正在由另一个执行单元处理。"""


@dataclass(frozen=True)
class IdempotentResult:
    """幂等业务动作的响应和资源标识。"""

    response: dict[str, object]
    resource_type: str
    resource_id: str


IdempotentOperation = Callable[[AsyncSession | None], Awaitable[IdempotentResult]]


class IdempotencyService:
    """确保成功响应只在数据库提交后写入 Redis。"""

    def __init__(self, repository: IdempotencyRepository | None = None) -> None:
        self.repository = repository or IdempotencyRepository()

    @staticmethod
    def _decode(response_json: str) -> dict[str, object]:
        return cast(dict[str, object], json.loads(response_json))

    async def _find_committed(
        self,
        user_id: str,
        request_id: str,
        action_type: str,
    ) -> dict[str, object] | None:
        async with transaction() as session:
            record = await self.repository.find(session, user_id, request_id, action_type)
            return self._decode(record.response_json) if record is not None else None

    async def execute(
        self,
        *,
        user_id: str,
        request_id: str,
        action_type: str,
        operation: IdempotentOperation,
    ) -> dict[str, object]:
        """执行一次写操作，重复请求返回第一次已经提交的响应。"""
        key = make_idempotency_key(user_id, request_id, action_type)
        probe = await idempotency_store.probe(key, use_redis=settings.use_database)
        if not probe.acquired:
            if probe.cached_response in (None, idempotency_store.pending_value):
                raise IdempotencyInProgress("请求正在处理中")
            return self._decode(probe.cached_response)

        try:
            if settings.use_database:
                result = await self._execute_database(
                    user_id=user_id,
                    request_id=request_id,
                    action_type=action_type,
                    operation=operation,
                )
            else:
                result = await operation(None)
            response_json = json.dumps(result.response, ensure_ascii=False, separators=(",", ":"))
            await idempotency_store.complete(key, response_json, use_redis=settings.use_database)
            return result.response
        except IntegrityError:
            # 唯一索引冲突说明并发请求已提交；查回其结果而不是再次执行。
            committed = await self._find_committed(user_id, request_id, action_type)
            if committed is None:
                await idempotency_store.release(key, use_redis=settings.use_database)
                raise
            await idempotency_store.complete(
                key,
                json.dumps(committed, ensure_ascii=False, separators=(",", ":")),
                use_redis=settings.use_database,
            )
            return committed
        except Exception:
            await idempotency_store.release(key, use_redis=settings.use_database)
            raise

    async def _execute_database(
        self,
        *,
        user_id: str,
        request_id: str,
        action_type: str,
        operation: IdempotentOperation,
    ) -> IdempotentResult:
        """在同一事务内完成业务写入和数据库幂等记录。"""
        async with transaction() as session:
            existing = await self.repository.find(session, user_id, request_id, action_type)
            if existing is not None:
                return IdempotentResult(
                    response=self._decode(existing.response_json),
                    resource_type=existing.resource_type,
                    resource_id=existing.resource_id,
                )
            result = await operation(session)
            await self.repository.add(
                session,
                user_id=user_id,
                request_id=request_id,
                action_type=action_type,
                resource_type=result.resource_type,
                resource_id=result.resource_id,
                response_json=json.dumps(result.response, ensure_ascii=False, separators=(",", ":")),
            )
            return result


idempotency_service = IdempotencyService()
