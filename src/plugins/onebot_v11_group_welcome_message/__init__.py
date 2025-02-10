"""
@Author         : Ailitonia
@Date           : 2023/7/17 0:07
@FileName       : onebot_v11_group_welcome_message
@Project        : nonebot2_miya
@Description    : QQ 群自定义欢迎消息
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='群欢迎消息',
    description='【QQ 群自定义欢迎消息插件】\n'
                '向新入群的成员发送欢迎消息',
    usage='/设置欢迎消息 [消息内容]\n'
          '/移除欢迎消息',
    supported_adapters={'OneBot V11'},
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
