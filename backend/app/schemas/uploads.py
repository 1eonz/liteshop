"""文件上传签名 DTO。"""

from typing import Annotated

from pydantic import BaseModel, Field


class UploadSignRequest(BaseModel):
    """上传签名请求。"""

    file_name: Annotated[str, Field(alias="fileName", min_length=1, max_length=255)]
    file_size: Annotated[int, Field(alias="fileSize", gt=0)]
    content_type: Annotated[str, Field(alias="contentType", min_length=1, max_length=100)]
    model_config = {"populate_by_name": True}
