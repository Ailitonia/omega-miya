"""
@Author         : Ailitonia
@Date           : 2021/12/24 11:09
@FileName       : roll.py
@Project        : nonebot2_miya
@Description    : 骰子插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='Roll',
    description='【骰子插件】\n'
                '各种姿势的掷骰子',
    usage='/roll num\n'
          '/roll AdB(kq)C(pb)DaE\n'
          '/rd\n'
          '/ra\n'
          '/r(bp)',
    extra={'author': 'Ailitonia'},
)  # TODO 开发中


from . import command as command


__all__ = []
