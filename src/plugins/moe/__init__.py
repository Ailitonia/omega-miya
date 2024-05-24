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
          '/来点涩图 [关键词, ...]\n\n'
          '仅限管理员使用:\n'
          '/图库统计\n'
          '/图库查询 [关键词, ...]\n'
          '/导入图库',
    config=None,
    extra={'author': 'Ailitonia'},
)

from . import command as command


__all__ = []
