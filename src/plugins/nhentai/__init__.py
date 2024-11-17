"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午10:52
@FileName       : nhentai
@Project        : nonebot2_miya
@Description    : Nhentai
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='nhentai',
    description='【nhentai】\n'
                '神秘的插件',
    usage='/nh [id]\n'
          '/nh_preview [id]\n'
          '/nh_search [tag]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
