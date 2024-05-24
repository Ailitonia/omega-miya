"""
@Author         : Ailitonia
@Date           : 2023/7/16 22:00
@FileName       : nbnhhsh
@Project        : nonebot2_miya
@Description    : nbnhhsh
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='好好说话',
    description='【能不能好好说话？】\n'
                '拼音首字母缩写释义',
    usage='/好好说话 [缩写]',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
