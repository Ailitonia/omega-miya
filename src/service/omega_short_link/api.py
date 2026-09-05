"""
@Author         : Ailitonia
@Date           : 2025/7/16 17:46:09
@FileName       : api.py
@Project        : omega-miya
@Description    : 短链接服务 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import uuid

from fastapi import HTTPException
from fastapi.responses import RedirectResponse
from nonebot import get_driver, logger

from .config import short_link_config
from ..apscheduler import scheduler
from ..omega_api import OmegaAPI
from ..omega_global_cache import OmegaGlobalCache

_SHORT_LINK_API = OmegaAPI(
    app_name='omega_short_link',
    enable_token_verify=False,
    access_domain=short_link_config.omega_short_link_access_domain,
    use_https=short_link_config.omega_short_link_use_https,
)
"""短链接服务 API"""

_SHORT_LINK_CACHE = OmegaGlobalCache(
    cache_name='omega_short_link',
    default_ttl=short_link_config.omega_short_link_cache_ttl,
)
"""短链接服务全局缓存"""


async def query_short_link_uuid(url: str, *, ttl_delta: int = 0) -> str:
    """获取网址短链接 UUID"""
    if not url.strip():
        raise ValueError('Invalid url')

    link_uuid = uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=url)
    await _SHORT_LINK_CACHE.save(link_uuid.hex, url, ttl_delta=ttl_delta)
    return link_uuid.hex


async def query_short_link_real_url(link_uuid: str, *, auto_refresh: bool = True) -> str | None:
    """根据短链接 UUID 获取真实网址"""
    url = await _SHORT_LINK_CACHE.load(link_uuid)
    if auto_refresh and url is not None:
        url = await _SHORT_LINK_CACHE.save(link_uuid, url)
    return url


if short_link_config.omega_short_link_enable_http_forward_service:

    # 注册短链接同步缓存定时任务
    @scheduler.scheduled_job(
        'cron',
        hour='3',
        minute='4',
        second='5',
        id='omega_short_link_sync_short_link_cache',
        coalesce=True,
    )
    @get_driver().on_startup
    async def _sync_short_link_cache() -> None:
        """同步短链接缓存"""
        try:
            await _SHORT_LINK_CACHE.sync_internal()
            logger.opt(colors=True).success('<lc>OmegaShortLink</lc> | <lg>短链接缓存同步成功</lg>')
        except Exception as e:
            logger.opt(colors=True).error(f'<lc>OmegaShortLink</lc> | <r>短链接缓存同步失败</r>, {e}')

    # 注册短链接转发服务 API
    @_SHORT_LINK_API.register_get_route('/go/{link_uuid}')
    async def _get_real_url(link_uuid: str) -> RedirectResponse:
        url = await query_short_link_real_url(link_uuid)

        if not url:
            raise HTTPException(status_code=404, detail='Short link expired or deleted')

        return RedirectResponse(url=url, status_code=307)

    logger.opt(colors=True).success('<lc>OmegaShortLink</lc> | <lg>短链接服务已启用</lg>')


__all__ = [
    'query_short_link_real_url',
    'query_short_link_uuid',
]
