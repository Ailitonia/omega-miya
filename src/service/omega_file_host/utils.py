"""
@Author         : Ailitonia
@Date           : 2025/5/30 11:31:11
@FileName       : utils.py
@Project        : omega-miya
@Description    : 文件缓存及路径处理工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import uuid
from typing import TYPE_CHECKING

from nonebot import get_driver, logger

from .config import file_host_config
from ..apscheduler import scheduler
from ..omega_global_cache import OmegaGlobalCache

if TYPE_CHECKING:
    from src.resource import BaseResource

_FILE_HOST_CACHE = OmegaGlobalCache(
    cache_name='omega_file_host',
    default_ttl=file_host_config.omega_file_host_cache_ttl,
)
"""初始化文件路径全局缓存"""


@scheduler.scheduled_job(
    'cron',
    minute='*/15',
    second='11',
    id='omega_file_host_sync_file_host_cache',
    coalesce=True,
)
@get_driver().on_startup
async def _sync_file_host_cache() -> None:
    """同步文件缓存"""
    try:
        await _FILE_HOST_CACHE.sync_internal()
        logger.opt(colors=True).success('<lc>OmegaFileHost</lc> | <lg>文件缓存同步成功</lg>')
    except Exception as e:
        logger.opt(colors=True).error(f'<lc>OmegaFileHost</lc> | <r>文件缓存同步失败</r>, {e}')


async def query_file_uuid(file: 'BaseResource', *, ttl_delta: int = 0) -> str:
    """获取文件 UUID"""
    file_uuid = uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=file.resolve_path)
    await _FILE_HOST_CACHE.save(file_uuid.hex, file.resolve_path, ttl_delta=ttl_delta)
    return file_uuid.hex


async def query_file_path(file_uuid: str) -> str | None:
    """根据 UUID 获取文件路径"""
    return await _FILE_HOST_CACHE.load(file_uuid)


__all__ = [
    'query_file_path',
    'query_file_uuid',
]
