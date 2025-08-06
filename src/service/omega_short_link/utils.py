"""
@Author         : Ailitonia
@Date           : 2025/7/16 17:25:19
@FileName       : utils.py
@Project        : omega-miya
@Description    : 短链接缓存及处理工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import uuid

from nonebot import get_driver, logger

from .config import short_link_config
from ..apscheduler import scheduler
from ..omega_global_cache import OmegaGlobalCache

_SHORT_LINK_CACHE = OmegaGlobalCache(
    cache_name='omega_short_link',
    default_ttl=short_link_config.omega_short_link_cache_ttl,
)
"""初始化短链接全局缓存"""


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


async def query_url_short_link_uuid(url: str, *, ttl_delta: int = 0) -> str:
    """获取网址短链接 UUID"""
    file_uuid = uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=url)
    await _SHORT_LINK_CACHE.save(file_uuid.hex, url, ttl_delta=ttl_delta)
    return file_uuid.hex


async def query_short_link_url(short_link_uuid: str, *, auto_refresh: bool = True) -> str | None:
    """根据 UUID 获取真实网址"""
    url = await _SHORT_LINK_CACHE.load(short_link_uuid)
    if auto_refresh and url is not None:
        await _SHORT_LINK_CACHE.save(short_link_uuid, url)
    return url


__all__ = [
    'query_short_link_url',
    'query_url_short_link_uuid',
]
