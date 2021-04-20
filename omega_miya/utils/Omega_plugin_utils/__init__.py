from typing import Optional
from nonebot.plugin import Export
from nonebot.typing import T_State
from .rules import *
from .encrypt import AESEncryptStr
from .cooldown import *
from .permission import *
from .http_fetcher import HttpFetcher
from .picture_encoder import PicEncoder


def init_export(
        plugin_export: Export,
        custom_name: str,
        usage: str,
        auth_node: list = None,
        cool_down: list = None,
        **kwargs: str) -> Export:
    setattr(plugin_export, 'custom_name', custom_name)
    setattr(plugin_export, 'usage', usage)
    setattr(plugin_export, 'auth_node', auth_node)
    setattr(plugin_export, 'cool_down', cool_down)
    for key, value in kwargs.items():
        setattr(plugin_export, key, value)
    return plugin_export


def init_permission_state(
        name: str,
        notice: Optional[bool] = None,
        command: Optional[bool] = None,
        level: Optional[int] = None,
        auth_node: Optional[str] = None) -> T_State:
    return {
        '_matcher': name,
        '_notice_permission': notice,
        '_command_permission': command,
        '_permission_level': level,
        '_auth_node': auth_node
    }


__all__ = [
    'init_export',
    'init_permission_state',
    'has_notice_permission',
    'has_command_permission',
    'has_auth_node',
    'has_level_or_node',
    'permission_level',
    'AESEncryptStr',
    'PluginCoolDown',
    'check_and_set_global_cool_down',
    'check_and_set_plugin_cool_down',
    'check_and_set_group_cool_down',
    'check_and_set_user_cool_down',
    'check_notice_permission',
    'check_command_permission',
    'check_permission_level',
    'check_auth_node',
    'HttpFetcher',
    'PicEncoder'
]
