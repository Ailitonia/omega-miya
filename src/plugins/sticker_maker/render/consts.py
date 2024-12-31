"""
@Author         : Ailitonia
@Date           : 2024/5/12 下午7:12
@FileName       : consts
@Project        : nonebot2_miya
@Description    : 标签包模板常量
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.resource import StaticResource, TemporaryResource

FONT_RESOURCE: StaticResource = StaticResource('fonts')
"""默认字体文件目录"""

STATIC_RESOURCE: StaticResource = StaticResource('images', 'sticker_maker')
"""表情包插件静态资源文件夹路径"""

STICKER_OUTPUT_PATH: TemporaryResource = TemporaryResource('sticker_maker', 'output')
"""生成表情包图片保存路径"""

TMP_PATH: TemporaryResource = TemporaryResource('sticker_maker', 'tmp')
"""下载外部资源图片的缓存文件"""


__all__ = [
    'FONT_RESOURCE',
    'STATIC_RESOURCE',
    'STICKER_OUTPUT_PATH',
    'TMP_PATH',
]
