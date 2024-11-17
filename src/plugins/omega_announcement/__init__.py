"""
@Author         : Ailitonia
@Date           : 2023/7/15 18:51
@FileName       : omega_announcement
@Project        : nonebot2_miya
@Description    : Omega 公告插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='公告',
    description='【公告插件】\n'
                '快速批量向启用了 Omega 功能的对象发送通知公告',
    usage='/公告 [公告内容]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
