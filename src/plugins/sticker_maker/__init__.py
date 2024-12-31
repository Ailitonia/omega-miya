"""
@Author         : Ailitonia
@Date           : 2024/5/12 下午7:09
@FileName       : __init__.py
@Project        : nonebot2_miya
@Description    : 表情包助手插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='表情包',
    description='【表情包助手插件】\n'
                '使用模板快速制作表情包',
    usage='/表情包 [模板名][表情包图片][表情包文本]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
