"""
@Author         : Ailitonia
@Date           : 2022/12/02 21:44
@FileName       : consts.py
@Project        : nonebot2_miya
@Description    : Omega database consts
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from pydantic.dataclasses import dataclass


@dataclass
class BaseInternalNode:
    module: Literal['OmegaInternal'] = 'OmegaInternal'


class BaseInternalPermissionAuthNode(BaseInternalNode):
    plugin: Literal['OmegaInternal'] = 'OmegaInternal'


class PermissionGlobal(BaseInternalPermissionAuthNode):
    """全局功能开关权限"""
    node: Literal['OmegaPermissionGlobalEnable'] = 'OmegaPermissionGlobalEnable'


class PermissionLevel(BaseInternalPermissionAuthNode):
    """权限等级"""
    node: Literal['OmegaPermissionLevel'] = 'OmegaPermissionLevel'


class CharacterAttribute(BaseInternalNode):
    """对象角色属性"""
    plugin: Literal['OmegaInternalCharacterAttribute'] = 'OmegaInternalCharacterAttribute'


class CharacterProfile(BaseInternalNode):
    """对象角色档案"""
    plugin: Literal['OmegaInternalCharacterProfile'] = 'OmegaInternalCharacterProfile'


SKIP_COOLDOWN_PERMISSION_NODE: Literal['OmegaAllowSkipCooldown'] = 'OmegaAllowSkipCooldown'
"""允许跳过冷却权限节点"""

GLOBAL_COOLDOWN_EVENT: Literal['OmegaGlobalCooldown'] = 'OmegaGlobalCooldown'
"""全局冷却 event 名称"""

CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX: Literal['OmegaICAttrSetter'] = 'OmegaICAttrSetter'
"""对象角色属性设置冷却 event 名称, OmegaInternalCharacterAttributeSetter"""

CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX: Literal['OmegaICProfileSetter'] = 'OmegaICProfileSetter'
"""对象角色档案设置冷却 event 名称, OmegaInternalCharacterProfileSetter"""


__all__ = [
    'PermissionGlobal',
    'PermissionLevel',
    'CharacterAttribute',
    'CharacterProfile',
    'SKIP_COOLDOWN_PERMISSION_NODE',
    'GLOBAL_COOLDOWN_EVENT',
    'CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX',
    'CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX',
]
