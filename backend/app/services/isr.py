"""官网 ISR 失效通知服务。"""

from collections.abc import Sequence

import httpx2
import structlog

from ..core.config import settings

logger = structlog.get_logger(__name__)


async def trigger_isr_revalidate(slug: str, *, tags: Sequence[str] = ()) -> bool:
    """通知 Next.js 失效指定页面；通知失败不影响已提交的后台数据。"""
    if not settings.nextjs_base_url or not settings.revalidate_token:
        return False
    url = f"{settings.nextjs_base_url.rstrip('/')}/api/revalidate"
    try:
        async with httpx2.AsyncClient(timeout=settings.revalidate_timeout_seconds) as client:
            response = await client.post(
                url,
                json={"slug": slug, "tags": list(tags)},
                headers={"x-revalidate-token": settings.revalidate_token},
            )
        if response.status_code >= 400:
            logger.warning("site_isr_revalidate_failed", slug=slug, status_code=response.status_code)
            return False
        logger.info("site_isr_revalidated", slug=slug)
        return True
    except Exception as error:  # 网络依赖不可用时保留已保存页面，等待后续重试任务。
        logger.warning("site_isr_revalidate_unavailable", slug=slug, error=str(error))
        return False
