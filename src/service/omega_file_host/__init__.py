"""
@Author         : Ailitonia
@Date           : 2025/5/30 11:11:36
@FileName       : omega_file_host.py
@Project        : omega-miya
@Description    : 文件托管服务, 通过 HTTP API 提供文件内容
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from src.resource import AnyResource, StaticResource, TemporaryResource

from .api import OmegaFileHostProtocol

# 统一为本地资源注册 `OmegaFileHostProtocol`
AnyResource.register_host_protocol(OmegaFileHostProtocol)
StaticResource.register_host_protocol(OmegaFileHostProtocol)
TemporaryResource.register_host_protocol(OmegaFileHostProtocol)

__all__ = []
