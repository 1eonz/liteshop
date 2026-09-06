"""用户状态枚举。"""

from enum import StrEnum


class UserStatus(StrEnum):
    """商城用户账号状态。"""

    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
