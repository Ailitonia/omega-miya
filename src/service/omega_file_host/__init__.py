"""
@Author         : Ailitonia
@Date           : 2025/5/30 11:11:36
@FileName       : omega_file_host.py
@Project        : omega-miya
@Description    : 文件托管服务, 通过 HTTP API 提供文件内容
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.resource import AnyResource, BaseResource, BaseResourceHostProtocol, StaticResource, TemporaryResource
from .api import get_file_download_url, query_file_real_path, query_file_uuid
from .config import file_host_config


class OmegaFileHostProtocol[RT: BaseResource](BaseResourceHostProtocol[RT]):
    """Omega 文件托管服务实现"""

    async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> str:
        if file_host_config.omega_file_host_enable_hosting_service:
            file_uuid = await query_file_uuid(self._resource, ttl_delta=ttl_delta)
            return get_file_download_url(file_uuid)
        else:
            return self._resource.resolve_path


# 统一为本地资源注册 `OmegaFileHostProtocol`
AnyResource.register_host_protocol(OmegaFileHostProtocol)
StaticResource.register_host_protocol(OmegaFileHostProtocol)
TemporaryResource.register_host_protocol(OmegaFileHostProtocol)


__all__ = [
    'get_file_download_url',
    'query_file_uuid',
    'query_file_real_path',
]
