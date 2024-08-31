"""
@Author         : Ailitonia
@Date           : 2024/6/26 上午3:25
@FileName       : jm
@Project        : nonebot2_miya
@Description    : 18Comic
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata


__plugin_meta__ = PluginMetadata(
    name='jm',
    description='【JM】\n'
                '神秘的插件',
    usage='/jm [id]\n'
          '/jm_preview [id]\n'
          '/jm_search [tag]',
    extra={'author': 'Ailitonia'},
)


from . import command as command


__all__ = []
