"""
@Author         : Ailitonia
@Date           : 2026/3/19 18:11
@FileName       : consts
@Project        : omega-miya
@Description    : 透明转发插件常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

VERIFICATION_CODE_ENTITY_KEY_PREFIX: str = 'entity_index_id_'
"""转发验证码全局缓存键名前缀"""
TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME: Literal['Omega.TransparentForward'] = 'Omega.TransparentForward'
"""固定写入数据库的 module name 参数"""
TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME: Literal['TransparentForward'] = 'TransparentForward'
"""固定写入数据库的 plugin name 参数"""
TRANSPARENT_FORWARD_TARGET_NODE_PREFIX: Literal['transparent_forward_target_'] = 'transparent_forward_target_'
"""固定写入数据库的转发目标 node 前缀"""

__all__ = [
    'TRANSPARENT_FORWARD_CUSTOM_MODULE_NAME',
    'TRANSPARENT_FORWARD_CUSTOM_PLUGIN_NAME',
    'TRANSPARENT_FORWARD_TARGET_NODE_PREFIX',
    'VERIFICATION_CODE_ENTITY_KEY_PREFIX',
]
