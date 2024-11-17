"""
@Author         : Ailitonia
@Date           : 2024/4/10 上午2:08
@FileName       : translate
@Project        : nonebot2_miya
@Description    : 翻译插件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot.plugin import PluginMetadata

__plugin_meta__ = PluginMetadata(
    name='翻译',
    description='【翻译插件】\n'
                '简单的翻译插件\n'
                '目前使用了腾讯云的翻译API',
    usage='/翻译 [翻译内容]',
    extra={'author': 'Ailitonia'},
)


from . import command as command

__all__ = []
