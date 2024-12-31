"""
@Author         : Ailitonia
@Date           : 2024/5/8 下午6:40
@FileName       : what_to_eat
@Project        : nonebot2_miya
@Description    : 今天吃啥插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='今天吃啥',
    description='【今天吃啥】\n'
                '给吃饭选择困难症一个解决方案',
    usage='/今天吃啥\n'
          '/早上吃啥\n'
          '/中午吃啥\n'
          '/晚上吃啥\n'
          '/夜宵吃啥',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
