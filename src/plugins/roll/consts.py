"""
@Author         : Ailitonia
@Date           : 2024/6/16 上午1:58
@FileName       : consts
@Project        : nonebot2_miya
@Description    : 骰子插件常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""


MODULE_NAME = str(__name__).rsplit('.', maxsplit=1)[0]
PLUGIN_NAME = MODULE_NAME.rsplit('.', maxsplit=1)[-1]
ATTR_PREFIX = 'Attr_'


__all__ = [
    'MODULE_NAME',
    'PLUGIN_NAME',
    'ATTR_PREFIX',
]
