"""领域层异常，供服务层和 HTTP 适配层共享。"""


class ProductNotFound(KeyError):
    """商品不存在。"""


class AddressNotFound(KeyError):
    """收货地址不存在或不属于当前用户。"""
