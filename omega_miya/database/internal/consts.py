"""
@Author         : Ailitonia
@Date           : 2022/04/03 15:12
@FileName       : auth_node.py
@Project        : nonebot2_miya 
@Description    : Internal Consts
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal
from pydantic.dataclasses import dataclass


@dataclass
class BaseInternalAuthNode:
    module: Literal['OmegaInternal'] = 'OmegaInternal'
    plugin: Literal['OmegaInternal'] = 'OmegaInternal'


class PermissionGlobal(BaseInternalAuthNode):
    """全局功能开关权限"""
    node: Literal['OmegaPermissionGlobalEnable'] = 'OmegaPermissionGlobalEnable'


class PermissionLevel(BaseInternalAuthNode):
    """权限等级"""
    node: Literal['OmegaPermissionLevel'] = 'OmegaPermissionLevel'


SKIP_COOLDOWN_PERMISSION_NODE: Literal['skip_cooldown'] = 'skip_cooldown'
"""允许跳过冷却权限节点"""


GLOBAL_COOLDOWN_EVENT: Literal['OmegaGlobalCooldown'] = 'OmegaGlobalCooldown'
"""全局冷却 event 名称"""


RATE_LIMITING_COOLDOWN_EVENT: Literal['OmegaRateLimitingCooldown'] = 'OmegaRateLimitingCooldown'
"""流控限制冷却 event 名称"""


__all__ = [
    'PermissionGlobal',
    'PermissionLevel',
    'SKIP_COOLDOWN_PERMISSION_NODE',
    'GLOBAL_COOLDOWN_EVENT',
    'RATE_LIMITING_COOLDOWN_EVENT'
]
