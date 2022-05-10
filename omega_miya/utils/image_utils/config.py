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
from omega_miya.local_resource import LocalResource, TmpResource


@dataclass
class ImageUtilsConfig:
    """Image Utils 配置"""
    # 默认的生成缓存文件路径
    default_save_folder: TmpResource = TmpResource('image_utils')
    default_preview_img_folder: TmpResource = default_save_folder('preview')

    # 默认内置的静态资源文件路径
    default_font_name: str = 'SourceHanSans_Regular.otf'
    default_font_folder: LocalResource = LocalResource('fonts')
    default_font_file: LocalResource = default_font_folder(default_font_name)
    default_preview_font: LocalResource = default_font_folder('SourceHanSerif-Regular.ttc')


image_utils_config = ImageUtilsConfig()


__all__ = [
    'image_utils_config'
]
