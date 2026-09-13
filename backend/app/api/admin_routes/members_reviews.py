"""管理后台会员与评价路由。"""

from fastapi import APIRouter, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...errors import ApiError
from ...schemas.membership import MemberLevelUpdate, MemberTagsUpdate
from ...schemas.review import ReviewAudit, ReviewReply
from ...services.membership import MembershipError, membership_service
from ...services.review import review_service
from ..dependencies import CurrentSubject
from ..responses import success
from .common import admin_service, authorize_read, execute_write, require_database, session_dependency

router = APIRouter()


@router.get("/members")
async def list_members(
    subject: CurrentSubject,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, alias="pageSize", ge=1, le=100),
    session: AsyncSession = session_dependency,
) -> dict[str, object]:
    """会员分页列表。"""
    require_database()
    await authorize_read(session, subject, "member.read")
    return success(await membership_service.list_members(session, page, page_size))


@router.get("/members/{user_id}")
async def get_member(
    user_id: int, subject: CurrentSubject, session: AsyncSession = session_dependency
) -> dict[str, object]:
    """会员详情。"""
    require_database()
    await authorize_read(session, subject, "member.read")
    try:
        return success(await membership_service.get_member(session, user_id))
    except MembershipError as error:
        raise ApiError(status_code=404, code=40401, i18n_key="common.not_found", message=str(error)) from error


@router.put("/members/{user_id}/tags")
async def update_member_tags(
    user_id: int, payload: MemberTagsUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """幂等更新会员标签。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_member_tags:{user_id}",
        permission="member.write",
        resource_type="member",
        operation=lambda session, _user_id, _request_id: membership_service.update_tags(session, user_id, payload.tags),
    )


@router.put("/members/{user_id}/level")
async def update_member_level(
    user_id: int, payload: MemberLevelUpdate, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """幂等更新会员等级。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_member_level:{user_id}",
        permission="member.write",
        resource_type="member",
        operation=lambda session, _user_id, _request_id: membership_service.update_level(
            session, user_id, payload.member_level
        ),
    )


@router.get("/reviews")
async def list_reviews(subject: CurrentSubject, session: AsyncSession = session_dependency) -> dict[str, object]:
    """评价审核列表。"""
    require_database()
    await authorize_read(session, subject, "review.read")
    reviews = await review_service.list_for_audit(session)
    return success(
        {
            "items": [
                {
                    "id": review.id,
                    "productId": review.product_id,
                    "skuId": review.sku_id,
                    "userId": review.user_id,
                    "rating": review.rating,
                    "content": review.content,
                    "images": list(review.images),
                    "status": review.status,
                    "reason": review.audit_reason,
                    "merchantReply": review.merchant_reply,
                    "merchantRepliedAt": review.merchant_replied_at.isoformat()
                    if review.merchant_replied_at is not None
                    else None,
                    "createdAt": review.created_at.isoformat(),
                }
                for review in reviews
            ]
        }
    )


async def _reply_review_operation(
    session: AsyncSession | None, review_id: int, reply: str, user_id: str, request_id: str
) -> dict[str, object]:
    """在统一后台写事务中保存评价回复并写审计。"""
    if session is None:
        raise RuntimeError("数据库事务会话未初始化")
    await admin_service.require_permission(session, user_id, "review.write")
    response = await review_service.reply(session, review_id, reply)
    await admin_service.audit(
        session,
        user_id=user_id,
        resource_type="REVIEW",
        resource_id=review_id,
        action="REPLY",
        request_id=request_id,
        before_data=None,
        after_data=response,
    )
    return response


@router.put("/reviews/{review_id}/reply")
async def reply_review(
    review_id: int, payload: ReviewReply, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """保存已通过评价的商家回复。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_review_reply:{review_id}",
        permission="review.write",
        resource_type="review",
        operation=lambda session, user_id, request_id: _reply_review_operation(
            session, review_id, payload.reply, user_id, request_id
        ),
    )


@router.put("/reviews/{review_id}")
async def audit_review(
    review_id: int, payload: ReviewAudit, subject: CurrentSubject, x_request_id: str = Header(...)
) -> dict[str, object]:
    """审核评价并记录幂等操作。"""
    return await execute_write(
        subject=subject,
        request_id=x_request_id,
        action_type=f"admin_review_audit:{review_id}",
        permission="review.write",
        resource_type="review",
        operation=lambda session, _user_id, _request_id: review_service.audit(
            session, review_id, payload.status, payload.reason
        ),
    )
