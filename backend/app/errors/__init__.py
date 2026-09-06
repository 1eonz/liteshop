"""统一业务错误类型。"""


class ApiError(Exception):
    """可由 FastAPI 异常处理器序列化的业务错误。"""

    def __init__(
        self,
        *,
        status_code: int,
        code: int,
        i18n_key: str,
        message: str,
        field: str | None = None,
        details: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.i18n_key = i18n_key
        self.message = message
        self.field = field
        self.details = details
        self.headers = headers
