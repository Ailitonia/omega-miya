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


from . import command as command
from . import monitor as monitor


__all__ = []
