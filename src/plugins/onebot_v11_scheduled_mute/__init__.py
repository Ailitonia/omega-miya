"""
@Author         : Ailitonia
@Date           : 2024/9/9 19:20
@FileName       : onebot_v11_scheduled_mute
@Project        : omega-miya
@Description    : 群定时全体禁言
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='定时群禁言',
    description='【OneBot V11 定时群禁言插件】\n'
                '设置定时群禁言',
    usage='/设置定时群禁言\n'
          '/删除定时群禁言\n\n'
          'Crontab格式说明:\n'
          '*/1 *  *  *  *\n'
          '分|时|日|月|星期',
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
