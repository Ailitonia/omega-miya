"""
@Author         : Ailitonia
@Date           : 2022/04/10 0:16
@FileName       : config.py
@Project        : nonebot2_miya
@Description    : Image Utils Config
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from nonebot import get_plugin_config, logger
from pydantic import BaseModel, ConfigDict, ValidationError

from src.resource import StaticResource, TemporaryResource


class ImageUtilsConfig(BaseModel):
    """Image Utils 配置"""
    # 默认内置的静态资源文件路径
    image_utils_default_font_size: int = 18
    image_utils_default_font_name: str = 'SourceHanSansSC-Regular.otf'
    image_utils_preview_font_name: str = 'SourceHanSerif-Regular.ttc'
    image_utils_emoji_font_name: str = 'NotoEmoji-Regular.ttf'

    # 图片加载最大像素数限制, 防止解压炸弹, 默认值与 Pillow 的 Image.MAX_IMAGE_PIXELS 一致
    image_utils_max_image_pixels: int = 178_956_970
    # 默认缓存资源保存路径
    image_utils_tmp_folder_name: Literal['image_utils'] = 'image_utils'

    model_config = ConfigDict(extra='ignore')

    @property
    def default_font_size(self) -> int:
        return self.image_utils_default_font_size

    @property
    def max_image_pixels(self) -> int:
        return self.image_utils_max_image_pixels

    @staticmethod
    def get_custom_name_font(font_name: str) -> StaticResource:
        return StaticResource('fonts', font_name)

    @property
    def default_font(self) -> StaticResource:
        return StaticResource('fonts', self.image_utils_default_font_name)

    @property
    def preview_font(self) -> StaticResource:
        return StaticResource('fonts', self.image_utils_preview_font_name)

    @property
    def emoji_font(self) -> StaticResource:
        return StaticResource('fonts', self.image_utils_emoji_font_name)

    @property
    def default_output_folder(self) -> TemporaryResource:
        return TemporaryResource(self.image_utils_tmp_folder_name, 'output')

    @property
    def default_preview_output_folder(self) -> TemporaryResource:
        return TemporaryResource(self.image_utils_tmp_folder_name, 'preview')

    @property
    def default_tmp_download_folder(self) -> TemporaryResource:
        return TemporaryResource(self.image_utils_tmp_folder_name, 'download')


try:
    image_utils_config = get_plugin_config(ImageUtilsConfig)
except ValidationError as e:
    import sys

    logger.opt(colors=True).critical(f'<r>ImageUtils 配置格式验证失败</r>, 错误信息:\n{e}')
    sys.exit(f'ImageUtils 配置格式验证失败, {e}')


__all__ = [
    'image_utils_config',
]
