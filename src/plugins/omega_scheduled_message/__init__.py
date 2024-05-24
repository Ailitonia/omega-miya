"""
@Author         : Ailitonia
@Date           : 2023/7/15 23:03
@FileName       : omega_scheduled_message
@Project        : nonebot2_miya
@Description    : Omega 定时消息插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='定时消息',
    description='【定时消息插件】\n'
                '设置定时消息',
    usage='/设置定时消息\n'
          '/删除定时消息\n'
          '/定时消息列表\n\n'
          'Crontab格式说明:\n'
          '*/1 *  *  *  *\n'
          '分|时|日|月|星期',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
