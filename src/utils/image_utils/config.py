"""
@Author         : Ailitonia
@Date           : 2022/04/10 0:16
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Image Utils Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass

from src.resource import StaticResource, TemporaryResource


@dataclass
class ImageUtilsConfig:
    """Image Utils 配置"""
    # 默认内置的静态资源文件路径
    default_font_size: int = 18
    default_font_name: str = 'SourceHanSansSC-Regular.otf'
    default_font_folder: StaticResource = StaticResource('fonts')
    default_font_file: StaticResource = default_font_folder(default_font_name)
    default_preview_font: StaticResource = default_font_folder('SourceHanSerif-Regular.ttc')
    default_emoji_font: StaticResource = default_font_folder('AppleColorEmoji.ttf')

    # 默认的生成缓存文件路径
    tmp_folder: TemporaryResource = TemporaryResource('image_utils')
    tmp_download_folder: TemporaryResource = tmp_folder('download')
    tmp_output_folder: TemporaryResource = tmp_folder('output')
    tmp_preview_output_folder: TemporaryResource = tmp_output_folder('preview')


image_utils_config = ImageUtilsConfig()


__all__ = [
    'image_utils_config'
]
