"""
@Author         : Ailitonia
@Date           : 2024/4/29 上午12:36
@FileName       : image_searcher
@Project        : nonebot2_miya
@Description    : 识图插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='识图搜番',
    description='【识图搜番插件】\n'
                '使用 SauceNAO/Ascii2d/Iqdb/trace.moe 识别各类图片、插画、番剧',
    usage='/识图 [图片]\n'
          '/搜番 [图片]',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
