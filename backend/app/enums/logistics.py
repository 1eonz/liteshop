"""一期预置物流公司代码。"""

from enum import StrEnum


class LogisticsCompanyCode(StrEnum):
    """物流公司代码，未知供应商统一使用 OTHER。"""

    SF = "SF"
    YTO = "YTO"
    ZTO = "ZTO"
    STO = "STO"
    YD = "YD"
    JT = "JT"
    EMS = "EMS"
    DBL = "DBL"
    JD = "JD"
    FAST = "FAST"
    OTHER = "OTHER"
