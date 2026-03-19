"""
@Author         : Ailitonia
@Date           : 2026/3/19 15:55
@FileName       : transparent_forward
@Project        : omega-miya
@Description    : 透明转发
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='透明转发',
    description='【透明转发】\n'
                '在任意平台间转发消息',
    usage='/生成透明转发验证码\n'
          '/绑定透明转发会话\n'
          '/移除透明转发会话',
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
