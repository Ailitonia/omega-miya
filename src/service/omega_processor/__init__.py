"""
@Author         : Ailitonia
@Date           : 2021/07/09 19:49
@FileName       : omega_processor
@Project        : nonebot2_miya 
@Description    : 统一处理冷却、权限等
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from . import onebot as onebot
from . import telegram as telegram
from . import universal as universal
from .plugin_utils import enable_processor_state

__all__ = [
    'enable_processor_state',
]
