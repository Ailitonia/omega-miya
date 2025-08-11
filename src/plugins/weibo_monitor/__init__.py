"""
@Author         : Ailitonia
@Date           : 2023/2/1 18:18
@FileName       : weibo_monitor
@Project        : nonebot2_miya
@Description    : 微博订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

from src.params.template import OmegaSubscriptionHandlerManager
from . import monitor as monitor
from .subscription_source import WeiboUserSubscriptionManager

__plugin_meta__ = PluginMetadata(
    name='微博订阅',
    description='【微博订阅插件】\n'
                '订阅并跟踪微博用户动态更新',
    usage='仅限私聊或群聊中群管理员使用:\n'
          '/微博订阅 [用户UID]\n'
          '/取消微博订阅 [用户UID]\n'
          '/微博订阅列表',
    extra={'author': 'Ailitonia'},
)

_weibo_handler_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=WeiboUserSubscriptionManager,
    command_prefix='微博',
    aliases_command_prefix={'微博用户'},
)
_weibo = _weibo_handler_manager.register_handlers()
"""注册微博订阅流程 Handlers"""


__all__ = []
