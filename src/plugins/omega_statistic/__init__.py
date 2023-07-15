"""
@Author         : Ailitonia
@Date           : 2021/08/15 1:19
@FileName       : omega_statistic.py
@Project        : nonebot2_miya
@Description    : 统计插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='统计信息',
    description='【OmegaStatistic 插件使用统计】\n'
                '查询插件使用情况',
    usage='/统计信息\n\n'
          '管理员命令:\n'
          '/statistic.bot-all',
    config=None,
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
