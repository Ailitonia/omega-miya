"""
@Author         : Ailitonia
@Date           : 2023/7/16 20:51
@FileName       : bot_message_recaller
@Project        : nonebot2_miya
@Description    : 快速撤回 bot 发送的消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='Bot消息撤回',
    description='【Bot 消息撤回插件】\n'
                '快速撤回 Bot 发送的消息\n'
                '仅限 SUPERUSER 使用',
    usage='回复或引用需撤回的消息\n'
          '/撤回',
    supported_adapters={'OneBot V11', 'Telegram'},
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
