"""
@Author         : Ailitonia
@Date           : 2023/7/16 2:28
@FileName       : onebot_v11_self_mute
@Project        : nonebot2_miya
@Description    : 随机口球
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='随机口球',
    description='【QQ 群随机口球插件】\n'
                '自取随机时长禁言礼包',
    usage='/随机口球 [n倍]',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
