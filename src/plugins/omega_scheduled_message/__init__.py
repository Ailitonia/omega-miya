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
    usage='/定时消息 新增 -n <任务名称> -c <crontab表达式> -m <消息内容>\n'
          '/定时消息 移除 -n <任务名称>\n'
          '/定时消息 清单\n\n'
          'Crontab格式说明:\n'
          '*/1 *  *  *  *\n'
          '分|时|日|月|星期\n'
          '星期字段 0 代表周一(APScheduler 语义)\n\n'
          '注意: 新增时 -m 选项须放在最后, 其后的全部内容均作为消息内容',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
