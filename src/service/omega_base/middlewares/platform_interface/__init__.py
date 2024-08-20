"""
@Author         : Ailitonia
@Date           : 2024/8/21 14:54:17
@FileName       : platform_interface
@Project        : omega-miya
@Description    : 平台操作兼容层
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .entity_target import entity_target_register
from .event_depend import event_depend_register
from .message_builder import message_builder_register

__all__ = [
    'entity_target_register',
    'event_depend_register',
    'message_builder_register',
]
