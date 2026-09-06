"""用户与地址 API DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field


class AddressCreate(BaseModel):
    """创建收货地址。"""

    receiver_name: Annotated[str, Field(alias="receiverName", min_length=1, max_length=50)]
    phone: Annotated[str, Field(min_length=6, max_length=20)]
    province_code: Annotated[str, Field(alias="provinceCode", min_length=1, max_length=20)]
    city_code: Annotated[str, Field(alias="cityCode", min_length=1, max_length=20)]
    district_code: Annotated[str, Field(alias="districtCode", min_length=1, max_length=20)]
    detail: Annotated[str, Field(min_length=1, max_length=500)]
    is_default: bool = Field(default=False, alias="isDefault")
    model_config = {"populate_by_name": True}


class AddressUpdate(BaseModel):
    """更新收货地址。"""

    receiver_name: Annotated[str | None, Field(default=None, alias="receiverName", min_length=1, max_length=50)]
    phone: Annotated[str | None, Field(default=None, min_length=6, max_length=20)]
    province_code: Annotated[str | None, Field(default=None, alias="provinceCode", min_length=1, max_length=20)]
    city_code: Annotated[str | None, Field(default=None, alias="cityCode", min_length=1, max_length=20)]
    district_code: Annotated[str | None, Field(default=None, alias="districtCode", min_length=1, max_length=20)]
    detail: Annotated[str | None, Field(default=None, min_length=1, max_length=500)]
    is_default: bool | None = Field(default=None, alias="isDefault")
    model_config = {"populate_by_name": True}
