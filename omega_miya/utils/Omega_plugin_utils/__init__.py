from typing import Optional
from nonebot.plugin.export import Export
from nonebot.typing import T_State
from .rules import OmegaRules
from .encrypt import AESEncryptStr
from .cooldown import PluginCoolDown
from .permission import PermissionChecker
from .http_fetcher import HttpFetcher
from .message_decoder import MessageDecoder
from .message_sender import MsgSender
from .picture_encoder import PicEncoder
from .picture_effector import PicEffector
from .process_utils import ProcessUtils
from .zip_utils import create_zip_file, create_7z_file


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
    'OmegaRules',
    'AESEncryptStr',
    'PluginCoolDown',
    'PermissionChecker',
    'HttpFetcher',
    'MessageDecoder',
    'MsgSender',
    'PicEncoder',
    'PicEffector',
    'ProcessUtils',
    'create_zip_file',
    'create_7z_file'
]
