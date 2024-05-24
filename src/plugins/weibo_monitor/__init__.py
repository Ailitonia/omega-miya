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


from . import command as command
from . import monitor as monitor


__all__ = []
