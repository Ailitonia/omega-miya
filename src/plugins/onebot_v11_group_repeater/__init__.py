"""
@Author         : Ailitonia
@Date           : 2023/7/17 3:51
@FileName       : __init__
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='复读姬',
    description='【QQ 群复读姬插件】\n'
                '如同人类的本质一样复读',
    usage='由群聊复读触发',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import common as common


__all__ = []
