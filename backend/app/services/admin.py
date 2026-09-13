"""管理后台服务兼容入口。

具体业务按领域拆分到商品、交易、权限和运费服务模块；本模块保留
``AdminService`` 与 ``AdminPermissionDenied``，避免现有 API、任务和测试破坏。
"""

from .admin_access import AdminAccessService
from .admin_catalog import AdminCatalogService
from .admin_core import AdminPermissionDenied
from .admin_freight import AdminFreightService
from .admin_trade import AdminTradeService

__all__ = ["AdminPermissionDenied", "AdminService"]


class AdminService(AdminCatalogService, AdminTradeService, AdminAccessService, AdminFreightService):
    """后台领域服务 facade，仅组合领域能力，不承载具体业务实现。"""


__all__ = ["AdminPermissionDenied", "AdminService"]
