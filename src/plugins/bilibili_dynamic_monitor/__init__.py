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

__plugin_meta__ = PluginMetadata(
    name='B站动态订阅',
    description='【B站动态订阅插件】\n'
                '订阅并跟踪Bilibili用户动态更新',
    usage='仅限私聊或群聊中群管理员使用:\n'
          '/B站动态订阅 [用户UID]\n'
          '/取消B站动态订阅 [用户UID]\n'
          '/B站动态订阅列表',
    extra={'author': 'Ailitonia'},
)


from . import command as command
from . import monitor as monitor

__all__ = []
