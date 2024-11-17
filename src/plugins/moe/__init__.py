"""
@Author         : Ailitonia
@Date           : 2023/8/27 19:12
@FileName       : moe
@Project        : nonebot2_miya
@Description    : 来点萌图
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='来点萌图',
    description='【图库插件】\n'
                '随机萌图和随机涩图\n'
                '不可以随意涩涩!',
    usage='/来点萌图 [关键词, ...]\n'
          '/来点涩图 [关键词, ...]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
