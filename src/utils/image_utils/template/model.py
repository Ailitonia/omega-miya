"""
@Author         : Ailitonia
@Date           : 2022/04/16 23:59
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : 图片生成数据统一模型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict


class ImageUtilsBaseModel(BaseModel):
    """图片实用工具数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True)


class PreviewImageThumbs(ImageUtilsBaseModel):
    """预览图中的缩略图数据"""
    desc_text: str
    preview_thumb: bytes


class PreviewImageModel(ImageUtilsBaseModel):
    """生成预览图的数据 Model"""
    preview_name: str
    count: int
    previews: list[PreviewImageThumbs]


__all__ = [
    'PreviewImageThumbs',
    'PreviewImageModel'
]
