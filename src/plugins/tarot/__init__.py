"""
@Author         : Ailitonia
@Date           : 2024/4/2 0:22
@FileName       : __init__
@Project        : nonebot2_miya
@Description    : 塔罗插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='塔罗牌',
    description='【塔罗牌插件】\n'
                '简单的塔罗牌插件',
    usage='/塔罗牌 [卡牌名]\n\n'
          '仅限私聊或群聊中群管理员使用:\n'
          '/设置塔罗牌组 [资源名]',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
