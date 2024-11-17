"""
@Author         : Ailitonia
@Date           : 2022/12/11 16:32
@FileName       : template.py
@Project        : nonebot2_miya 
@Description    : 常用的图片生成模板
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from .model import PreviewImageModel, PreviewImageThumbs
from .template_preview import generate_thumbs_preview_image

__all__ = [
    'PreviewImageThumbs',
    'PreviewImageModel',
    'generate_thumbs_preview_image'
]
