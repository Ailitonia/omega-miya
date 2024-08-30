"""
@Author         : Ailitonia
@Date           : 2023/8/30 21:42
@FileName       : pixivision
@Project        : nonebot2_miya
@Description    : Pixivision plugin
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='Pixivision',
    description='【Pixivision 特辑助手】\n'
                '探索并查看Pixivision文章\n'
                '订阅最新的Pixivision特辑',
    usage='/pixivision列表 [page]\n'
          '/pixivision特辑 [aid]\n\n'
          '仅限私聊或群聊中群管理员使用:\n'
          '/pixivision订阅\n'
          '/取消pixivision订阅',
    extra={'author': 'Ailitonia'},
)


from . import command as command
from . import monitor as monitor


__all__ = []
