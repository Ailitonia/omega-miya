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


@dataclass(frozen=True)
class _BaseInternalNode:
    module: Literal['OmegaInternal'] = 'OmegaInternal'


@dataclass(frozen=True)
class _BaseInternalPermissionAuthNode(_BaseInternalNode):
    plugin: Literal['OmegaInternal'] = 'OmegaInternal'


@dataclass(frozen=True)
class _PermissionGlobal(_BaseInternalPermissionAuthNode):
    """全局功能开关权限"""
    node: Literal['OmegaPermissionGlobalEnable'] = 'OmegaPermissionGlobalEnable'


@dataclass(frozen=True)
class _PermissionLevel(_BaseInternalPermissionAuthNode):
    """权限等级"""
    node: Literal['OmegaPermissionLevel'] = 'OmegaPermissionLevel'


@dataclass(frozen=True)
class _CharacterAttribute(_BaseInternalNode):
    """对象角色属性"""
    plugin: Literal['OmegaInternalCharacterAttribute'] = 'OmegaInternalCharacterAttribute'


@dataclass(frozen=True)
class _CharacterProfile(_BaseInternalNode):
    """对象角色档案"""
    plugin: Literal['OmegaInternalCharacterProfile'] = 'OmegaInternalCharacterProfile'


OMEGA_PERM_GLOBAL_NODE: _PermissionGlobal = _PermissionGlobal()
"""内置全局权限节点"""
OMEGA_PERM_LEVEL_NODE: _PermissionLevel = _PermissionLevel()
"""内置等级权限节点"""

OMEGA_ICA_ATTR_NODE: _CharacterAttribute = _CharacterAttribute()
"""对象角色属性节点"""
OMEGA_ICA_PROFILE_NODE: _CharacterProfile = _CharacterProfile()
"""对象角色档案节点"""

SKIP_COOLDOWN_PERMISSION_NODE: Literal['OmegaAllowSkipCooldown'] = 'OmegaAllowSkipCooldown'
"""允许跳过冷却权限节点"""
GLOBAL_COOLDOWN_EVENT: Literal['OmegaGlobalCooldown'] = 'OmegaGlobalCooldown'
"""全局冷却 event 名称"""
CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX: Literal['OmegaICAttrSetter'] = 'OmegaICAttrSetter'
"""对象角色属性设置冷却 event 名称, OmegaInternalCharacterAttributeSetter"""
CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX: Literal['OmegaICProfileSetter'] = 'OmegaICProfileSetter'
"""对象角色档案设置冷却 event 名称, OmegaInternalCharacterProfileSetter"""


__all__ = [
    'CHARACTER_ATTRIBUTE_SETTER_COOLDOWN_EVENT_PREFIX',
    'CHARACTER_PROFILE_SETTER_COOLDOWN_EVENT_PREFIX',
    'GLOBAL_COOLDOWN_EVENT',
    'OMEGA_ICA_ATTR_NODE',
    'OMEGA_ICA_PROFILE_NODE',
    'OMEGA_PERM_GLOBAL_NODE',
    'OMEGA_PERM_LEVEL_NODE',
    'SKIP_COOLDOWN_PERMISSION_NODE',
]
