"""
@Author         : Ailitonia
@Date           : 2025/8/4 14:41:55
@FileName       : custom_depends.py
@Project        : omega-miya
@Description    : 自定义数据类子依赖
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .artwork import (
    ARTIST_CONTEXT_MANAGER,
    ARTWORK_CONTEXT_MANAGER,
    OPTIONAL_REPLY_ARTIST,
    OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST,
    OPTIONAL_REPLY_ARTWORK,
)

__all__ = [
    'ARTIST_CONTEXT_MANAGER',
    'ARTWORK_CONTEXT_MANAGER',
    'OPTIONAL_REPLY_ARTIST',
    'OPTIONAL_REPLY_ARTIST_OR_ARTWORK_ARTIST',
    'OPTIONAL_REPLY_ARTWORK',
]
