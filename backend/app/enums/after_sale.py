"""售后类型与状态机枚举。"""

from enum import StrEnum


class AfterSaleType(StrEnum):
    """售后业务类型。"""

    REFUND_ONLY = "REFUND_ONLY"
    RETURN_REFUND = "RETURN_REFUND"
    EXCHANGE = "EXCHANGE"


class AfterSaleStatus(StrEnum):
    """售后单状态。"""

    PENDING_REVIEW = "PENDING_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    WAITING_RETURN = "WAITING_RETURN"
    RETURNED = "RETURNED"
    REFUNDING = "REFUNDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


ALLOWED_AFTER_SALE_TRANSITIONS: dict[AfterSaleStatus, set[AfterSaleStatus]] = {
    AfterSaleStatus.PENDING_REVIEW: {AfterSaleStatus.APPROVED, AfterSaleStatus.REJECTED, AfterSaleStatus.CANCELLED},
    AfterSaleStatus.APPROVED: {AfterSaleStatus.WAITING_RETURN, AfterSaleStatus.REFUNDING, AfterSaleStatus.CANCELLED},
    AfterSaleStatus.WAITING_RETURN: {AfterSaleStatus.RETURNED, AfterSaleStatus.CANCELLED},
    AfterSaleStatus.RETURNED: {AfterSaleStatus.REFUNDING},
    AfterSaleStatus.REFUNDING: {AfterSaleStatus.COMPLETED},
    AfterSaleStatus.REJECTED: set(),
    AfterSaleStatus.COMPLETED: set(),
    AfterSaleStatus.CANCELLED: set(),
}
