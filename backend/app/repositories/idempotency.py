"""数据库幂等记录仓储。"""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.idempotency import IdempotencyRecord


class IdempotencyRepository:
    """Redis 之外的唯一键兜底。"""

    async def find(
        self, session: AsyncSession, user_id: str, request_id: str, action_type: str
    ) -> IdempotencyRecord | None:
        return cast(
            IdempotencyRecord | None,
            await session.scalar(
                select(IdempotencyRecord).where(
                    IdempotencyRecord.user_id == user_id,
                    IdempotencyRecord.request_id == request_id,
                    IdempotencyRecord.action_type == action_type,
                )
            ),
        )

    async def find_for_update(
        self, session: AsyncSession, user_id: str, request_id: str, action_type: str
    ) -> IdempotencyRecord | None:
        """锁定幂等记录，避免并发请求同时复用未完成响应。"""
        return cast(
            IdempotencyRecord | None,
            await session.scalar(
                select(IdempotencyRecord)
                .where(
                    IdempotencyRecord.user_id == user_id,
                    IdempotencyRecord.request_id == request_id,
                    IdempotencyRecord.action_type == action_type,
                )
                .with_for_update()
            ),
        )

    async def add(
        self,
        session: AsyncSession,
        *,
        user_id: str,
        request_id: str,
        action_type: str,
        resource_type: str,
        resource_id: str,
        response_json: str,
    ) -> IdempotencyRecord:
        record = IdempotencyRecord(
            user_id=user_id,
            request_id=request_id,
            action_type=action_type,
            resource_type=resource_type,
            resource_id=resource_id,
            response_json=response_json,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        return record
