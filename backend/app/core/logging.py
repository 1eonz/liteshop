"""structlog 结构化日志初始化。"""

import logging
import sys
from typing import cast

import structlog


def configure_logging() -> None:
    """配置标准库桥接和 JSON 结构化输出。"""
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s", force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger() -> structlog.stdlib.BoundLogger:
    """返回统一配置的结构化日志器。"""
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger())
