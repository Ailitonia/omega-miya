"""
@Author         : Ailitonia
@Date           : 2023/7/16 19:50
@FileName       : http_cat
@Project        : nonebot2_miya
@Description    : Get http cat
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='HttpCat',
    description='【HttpCat插件】\n'
                '用猫猫表示的http状态码',
    usage='/HttpCat <code>',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
