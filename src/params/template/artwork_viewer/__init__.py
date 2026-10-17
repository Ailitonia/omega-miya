"""
@Author         : Ailitonia
@Date           : 2026/10/17 14:13
@FileName       : __init__.py
@Project        : omega-miya
@Description    : omega 图站查询、详情与预览通用命令模板
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .handlers import ALLOW_R18_NODE, ArtworkProcessHandler, ArtworkViewerHandlerFactory

__all__ = [
    'ALLOW_R18_NODE',
    'ArtworkViewerHandlerFactory',
    'ArtworkProcessHandler',
]
