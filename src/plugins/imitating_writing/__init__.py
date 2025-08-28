"""
@Author         : Ailitonia
@Date           : 2025/8/28 14:54:23
@FileName       : imitating_writing.py
@Project        : omega-miya
@Description    : 模仿写作插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='模仿写作',
    description='【模仿写作插件】\n'
                '快速仿写小作文',
    usage='/模仿写作 [模板][关键词]\n'
          '/小作文 [模板][关键词]',
    extra={'author': 'Ailitonia'},
)

from . import command as command

__all__ = []
