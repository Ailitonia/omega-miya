"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午1:51
@FileName       : omega_any_artworks
@Project        : omega-miya
@Description    : 图站作品浏览插件 (统一接口)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='看图',
    description='【图站作品浏览插件】\n'
                '浏览各个图站作品',
    usage='/<图站名称> [作品ID]\n'
          '/<图站名称> --random\n'
          '/<图站名称> --search [关键词]\n\n'
          '目前支持的图站: Danbooru, Gelbooru, Konachan, Yandere, Pixiv',
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
