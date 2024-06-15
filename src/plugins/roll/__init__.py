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
                '各种姿势的掷骰子\n'
                '不是跑团插件!',
    usage='简单掷骰: /roll [num]\n'
          '表达式掷骰: /roll.rd [AdB(kq)C(pb)DaE]\n'
          '检定骰点: /roll.ra [属性/技能名]\n'
          '属性骰点: /roll.rs [属性/技能名]\n'
          '属性清单: /roll.show\n\n'
          '说明:\n'
          '掷骰表达式含义为掷A个面数为B的多面骰子,然后计算它们的点数总和,即为该表达式的最终结果,即:\n'
          '[骰数]d[面数][[骰池参数]|[选取线参数][奖惩数参数]]\n'
          '骰池参数: a[点数阈值]\n'
          '选取线参数: (k|q)[选取个数]\n'
          '奖惩数参数: (p|b)[奖惩个数]\n\n'
          '鉴定骰点若用户未配置对应属性, 则需要先配置属性/技能值后使用, 配置属性需使用【roll.rs】命令\n\n'
          '为了娱乐效果, 只能通过随机骰点的形式配置属性, 单一属性重随冷却时间【6】小时',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
