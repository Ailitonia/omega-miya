"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午6:55
@FileName       : config
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from dataclasses import dataclass
from src.resource import StaticResource, TemporaryResource


@dataclass
class NhentaiConfig:
    """Nhentai 配置"""
    # 默认字体文件
    default_font_file: StaticResource = StaticResource('fonts', 'fzzxhk.ttf')
    # 默认的下载文件路径
    default_download_folder: TemporaryResource = TemporaryResource('nhentai', 'download')
    # 预览图生成路径
    default_preview_img_folder: TemporaryResource = TemporaryResource('nhentai', 'preview')
    default_preview_size: tuple[int, int] = (224, 327)  # 默认预览图缩略图大小


nhentai_config = NhentaiConfig()


__all__ = [
    'nhentai_config'
]
