"""
@Author         : Ailitonia
@Date           : 2024/3/26 22:57
@FileName       : pixiv
@Project        : nonebot2_miya
@Description    : Pixiv 用户作品助手
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='Pixiv用户作品助手',
    description='【Pixiv用户作品助手插件】\n'
                '查看Pixiv用户作品、用户日榜、周榜以及月榜\n'
                '订阅并跟踪画师作品更新',
    usage='/pixiv用户搜索 [用户昵称]\n'
          '/pixiv用户作品 <UID> [page]\n'
          '/pixiv用户收藏 [UID] [page]\n'
          '/pixiv用户日榜 [页码]\n'
          '/pixiv用户周榜 [页码]\n'
          '/pixiv用户月榜 [页码]\n'
          '/pixiv用户订阅列表\n\n'
          '仅限私聊或群聊中群管理员使用:\n'
          '/pixiv用户订阅 <UID>\n'
          '/取消pixiv用户订阅 <UID>',
    extra={'author': 'Ailitonia'},
)


from . import command as command
from . import monitor as monitor

__all__ = []
