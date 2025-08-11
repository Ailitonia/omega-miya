"""
@Author         : Ailitonia
@Date           : 2023/8/5 15:06
@FileName       : bilibili_dynamic_monitor
@Project        : nonebot2_miya
@Description    : Bilibili 用户动态订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

from src.params.template import OmegaSubscriptionHandlerManager
from . import monitor as monitor
from .subscription_source import BilibiliDynamicSubscriptionManager

__plugin_meta__ = PluginMetadata(
    name='B站用户动态订阅',
    description='【B站用户动态订阅插件】\n'
                '订阅并跟踪Bilibili用户动态更新',
    usage='仅限私聊或群聊中群管理员使用:\n'
          '/B站用户动态订阅 [用户UID]\n'
          '/取消B站用户动态订阅 [用户UID]\n'
          '/B站用户动态订阅列表',
    extra={'author': 'Ailitonia'},
)

_bilibili_dynamic_handler_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=BilibiliDynamicSubscriptionManager,
    command_prefix='B站用户动态',
    aliases_command_prefix={
        'b站用户动态',
        'Bilibili动态',
        'bilibili动态',
        'Bilibili用户动态',
        'bilibili用户动态',
    },
)
_bilibili_dynamic = _bilibili_dynamic_handler_manager.register_handlers()
"""注册B站用户动态订阅流程 Handlers"""


__all__ = []
