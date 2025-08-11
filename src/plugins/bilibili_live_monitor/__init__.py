"""
@Author         : Ailitonia
@Date           : 2022/04/28 20:26
@FileName       : bilibili_live_monitor
@Project        : nonebot2_miya
@Description    : Bilibili 直播间订阅
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

from src.params.template import OmegaSubscriptionHandlerManager
from . import monitor as monitor
from .subscription_source import BilibiliLiveRoomSubscriptionManager

__plugin_meta__ = PluginMetadata(
    name='B站直播间订阅',
    description='【B站直播间订阅插件】\n'
                '订阅并监控Bilibili直播间状态\n'
                '提供开播、下播、直播间换标题提醒',
    usage='仅限私聊或群聊中群管理员使用:\n'
          '/B站直播间订阅 [直播间房间号]\n'
          '/取消B站直播间订阅 [直播间房间号]\n'
          '/B站直播间订阅列表',
    extra={'author': 'Ailitonia'},
)

_bilibili_dynamic_handler_manager = OmegaSubscriptionHandlerManager(
    subscription_manager=BilibiliLiveRoomSubscriptionManager,
    command_prefix='B站直播间',
    aliases_command_prefix={
        'b站直播间',
        'Bilibili直播间',
        'bilibili直播间',
    },
)
_bilibili_dynamic = _bilibili_dynamic_handler_manager.register_handlers()
"""注册B站直播间订阅流程 Handlers"""


__all__ = []
