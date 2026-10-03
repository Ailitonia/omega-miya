"""
@Author         : Ailitonia
@Date           : 2026/10/3 12:37
@FileName       : input_data_from_v1
@Project        : omega-miya
@Description    : v1 核心数据导入工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .artwork import artwork_main
from .core import core_main

artwork_main = artwork_main
core_main = core_main


__all__ = [
    'artwork_main',
    'core_main',
]
