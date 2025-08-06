"""
@Author         : Ailitonia
@Date           : 2025/5/30 11:12:41
@FileName       : api.py
@Project        : omega-miya
@Description    : 文件托管服务 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nonebot.log import logger

from src.resource import AnyResource, BaseResource, BaseResourceHostProtocol
from .config import file_host_config
from .utils import query_file_path, query_file_uuid
from ..omega_api import OmegaAPI

_FILE_HOST_API = OmegaAPI(
    app_name='omega_file_host',
    access_domain=file_host_config.omega_file_host_access_domain,
    use_https=file_host_config.omega_file_host_use_https,
)
"""文件服务 API"""

if file_host_config.omega_file_host_enable_hosting_service:

    # 注册文件托管服务 API
    @_FILE_HOST_API.register_get_route('/download/{file_id}')
    async def _download_file(file_id: str) -> FileResponse:
        file_path = await query_file_path(file_id)

        if not file_path:
            raise HTTPException(status_code=404, detail='File expired or deleted')

        file = AnyResource(file_path)
        if not file.is_file:
            raise HTTPException(status_code=404, detail='File not found')

        return FileResponse(
            path=file.path,
            filename=f'{file_id}{file.suffix}',
            media_type='application/octet-stream',
        )

    logger.opt(colors=True).success('<lc>OmegaFileHost</lc> | <lg>文件托管服务已启用</lg>')


class OmegaFileHostProtocol(BaseResourceHostProtocol[BaseResource]):
    """Omega 文件托管服务实现"""

    async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> str:
        if file_host_config.omega_file_host_enable_hosting_service:
            file_uuid = await query_file_uuid(self._resource, ttl_delta=ttl_delta)
            return f'{_FILE_HOST_API.root_url}/download/{file_uuid}'
        else:
            return self._resource.resolve_path


__all__ = [
    'OmegaFileHostProtocol',
]
