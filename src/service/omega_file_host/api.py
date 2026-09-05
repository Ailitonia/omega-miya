"""
@Author         : Ailitonia
@Date           : 2025/5/30 11:12:41
@FileName       : api.py
@Project        : omega-miya
@Description    : 文件托管服务 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pathlib
import uuid
from typing import TYPE_CHECKING

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nonebot import get_driver, logger

from .config import file_host_config
from ..apscheduler import scheduler
from ..omega_api import OmegaAPI
from ..omega_global_cache import OmegaGlobalCache

if TYPE_CHECKING:
    from src.resource import BaseResource


_FILE_HOST_API = OmegaAPI(
    app_name='omega_file_host',
    enable_token_verify=False,
    access_domain=file_host_config.omega_file_host_access_domain,
    use_https=file_host_config.omega_file_host_use_https,
)
"""文件托管服务 API"""

_FILE_HOST_CACHE = OmegaGlobalCache(
    cache_name='omega_file_host',
    default_ttl=file_host_config.omega_file_host_cache_ttl,
)
"""文件托管服务文件路径全局缓存"""


async def query_file_uuid(file: 'BaseResource', *, ttl_delta: int = 0) -> str:
    """获取文件托管 UUID"""
    if not file.is_file:
        raise ValueError('Invalid file')

    file_uuid = uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=file.resolve_path)
    await _FILE_HOST_CACHE.save(file_uuid.hex, file.resolve_path, ttl_delta=ttl_delta)
    return file_uuid.hex


async def query_file_real_path(file_uuid: str, *, auto_refresh: bool = True) -> str | None:
    """根据 UUID 获取真实文件路径"""
    file_path = await _FILE_HOST_CACHE.load(file_uuid)
    if auto_refresh and file_path is not None:
        file_path = await _FILE_HOST_CACHE.save(file_uuid, file_path)
    return file_path


if file_host_config.omega_file_host_enable_hosting_service:

    # 注册文件托管服务同步缓存定时任务
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

    # 注册文件托管服务 API
    @_FILE_HOST_API.register_get_route('/download/{file_id}')
    async def _download_file(file_id: str) -> FileResponse:
        real_path = await query_file_real_path(file_id)

        if not real_path:
            raise HTTPException(status_code=404, detail='File expired or deleted')

        file_path = pathlib.Path(real_path)
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail='File not found')

        return FileResponse(
            path=file_path,
            filename=f'{file_id}{file_path.suffix}',
            media_type='application/octet-stream',
        )

    logger.opt(colors=True).success('<lc>OmegaFileHost</lc> | <lg>文件托管服务已启用</lg>')


def get_file_download_url(file_uuid: str) -> str:
    """获取文件下载地址"""
    return f'{_FILE_HOST_API.root_url}/download/{file_uuid}'


__all__ = [
    'get_file_download_url',
    'query_file_real_path',
    'query_file_uuid',
]
