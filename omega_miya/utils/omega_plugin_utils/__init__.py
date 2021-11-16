from typing import Optional, List
from nonebot.plugin.export import Export
from nonebot.typing import T_State
from .rules import OmegaRules
from .encrypt import AESEncryptStr
from .cooldown import PluginCoolDown
from .permission import PermissionChecker
from .http_fetcher import HttpFetcher
from .message_tools import MessageDecoder, MessageTools, EventTools, BotTools
from .message_sender import MsgSender
from .picture_encoder import PicEncoder
from .picture_effector import PicEffector
from .process_utils import ProcessUtils
from .role_utils import RoleChecker
from .text_utils import TextUtils
from .zip_utils import create_zip_file, create_7z_file


def init_export(
        plugin_export: Export,
        custom_name: str,
        usage: str,
        auth_node: Optional[List[str]] = None,
        **kwargs: str) -> Export:
    """
    初始化 export, 用于声明当前插件配置等信息, 用于 processor 等集中处理
    :param plugin_export: 当前插件 export
    :param custom_name: 插件自定义名称
    :param usage: 插件自定义用法说明
    :param auth_node: 插件所有可配置的权限节点
    :param kwargs: 其他自定义参数
    :return:
    """
    setattr(plugin_export, 'custom_name', custom_name)
    setattr(plugin_export, 'usage', usage)

    # 初始化默认权限节点
    if auth_node is not None:
        auth_node_ = set(auth_node)
        auth_node_.add(OmegaRules.basic_auth_node)
        auth_node_.add(PluginCoolDown.skip_auth_node)
        auth_node_ = list(auth_node_)
        auth_node_.sort()
    else:
        auth_node_ = [OmegaRules.basic_auth_node,
                      PluginCoolDown.skip_auth_node]
    setattr(plugin_export, 'auth_node', auth_node_)

    for key, value in kwargs.items():
        setattr(plugin_export, key, value)
    return plugin_export


def init_processor_state(
        name: str,
        notice: bool = False,
        command: bool = False,
        level: Optional[int] = None,
        auth_node: str = OmegaRules.basic_auth_node,
        cool_down: Optional[List[PluginCoolDown]] = None,
        enable_cool_down_check: bool = True
) -> T_State:
    """
    matcher state 初始化函数, 用于声明当前 matcher 权限及冷却等信息, 用于 processor 集中处理
    :param name: 自定义名称, 用于识别 matcher
    :param notice: 是否需要通知权限
    :param command: 是否需要命令权限
    :param level: 需要等级权限
    :param auth_node: 需要的权限节点名称
    :param cool_down: 需要的冷却时间配置
    :param enable_cool_down_check: 是否启用冷却检测, 部分无响应或被动响应的 matcher 应视情况将本选项设置为 False
    :return:
    """
    return {
        '_matcher_name': name,
        '_notice_permission': notice,
        '_command_permission': command,
        '_permission_level': level,
        '_auth_node': auth_node,
        '_cool_down': cool_down,
        '_enable_cool_down_check': enable_cool_down_check
    }


__all__ = [
    'init_export',
    'init_processor_state',
    'OmegaRules',
    'AESEncryptStr',
    'PluginCoolDown',
    'PermissionChecker',
    'HttpFetcher',
    'MessageDecoder',
    'MessageTools',
    'EventTools',
    'BotTools',
    'MsgSender',
    'PicEncoder',
    'PicEffector',
    'ProcessUtils',
    'RoleChecker',
    'TextUtils',
    'create_zip_file',
    'create_7z_file'
]
