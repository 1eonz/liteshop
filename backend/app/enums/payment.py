"""支付渠道枚举。"""

from enum import StrEnum


class PaymentProvider(StrEnum):
    """一期支持的支付渠道。"""

    WECHAT = "WECHAT"
    ALIPAY = "ALIPAY"


class PaymentStatus(StrEnum):
    """支付单独立生命周期状态。"""

    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
