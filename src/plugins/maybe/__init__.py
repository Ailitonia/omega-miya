"""
@Author         : Ailitonia
@Date           : 2023/7/16 17:21
@FileName       : maybe
@Project        : nonebot2_miya
@Description    : 求签插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='求签',
    description='【求签插件】\n'
                '求签, 求运势, 包括且不限于抽卡、吃饭、睡懒觉、DD\n'
                '每个人每天求同一个东西的结果是一样的啦!\n'
                '不要不信邪重新抽啦!',
    usage='/求签 [所求之事]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
