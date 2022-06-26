"""
@Author         : Ailitonia
@Date           : 2022/04/09 16:22
@FileName       : config.py
@Project        : nonebot2_miya 
@Description    : Text Utils Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from omega_miya.local_resource import LocalResource, TmpResource


@dataclass
class TextUtilsConfig:
    """Text Utils 配置"""
    # 默认内置的静态资源文件路径
    default_size: int = 18
    default_font_name: str = 'SourceHanSansSC-Regular.otf'
    default_font_folder: LocalResource = LocalResource('fonts')
    default_font_file: LocalResource = default_font_folder(default_font_name)
    default_emoji_font: LocalResource = default_font_folder('AppleColorEmoji.ttf')

    # 默认的生成缓存文件路径
    default_tmp_folder: TmpResource = TmpResource('text_utils')
    default_download_tmp_folder: TmpResource = default_tmp_folder('download')
    default_img_tmp_folder: TmpResource = default_tmp_folder('image')

    class Config:
        extra = "ignore"


text_utils_config = TextUtilsConfig()


__all__ = [
    'text_utils_config'
]
