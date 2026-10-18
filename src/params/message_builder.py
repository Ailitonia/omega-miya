"""
@Author         : Ailitonia
@Date           : 2026/10/18 23:03
@FileName       : message_builder
@Project        : omega-miya
@Description    : 通用消息段构造工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING

from nonebot_plugin_alconna.uniseg import Image

if TYPE_CHECKING:
    from src.resource import HostingPathType


def build_sendable_image(hosting_path: tuple['HostingPathType', str]) -> Image:
    """按托管路径类型构造 uniseg 图片消息段

    本地路径必须放入 Image.path 字段: uniseg Media 会将没有 hostname 的 url 自动改写为
    非法的 https:// 前缀 URL(Windows 盘符路径 urlparse 后 scheme='c' 而 netloc 为空)
    """
    path_type, path_value = hosting_path
    match path_type:
        case 'url':
            return Image(url=path_value)
        case 'path':
            return Image(path=path_value)
        case _:
            raise ValueError(f'Unsupported hosting path type: {path_type!r}')


__all__ = [
    'build_sendable_image',
]
