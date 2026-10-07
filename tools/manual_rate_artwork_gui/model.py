"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:06
@FileName       : model
@Project        : omega-miya
@Description    : 数据模型类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import BaseModel, ConfigDict, Field


class BaseRatingDataModel(BaseModel):
    """评级数据模型基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True, frozen=True)


class CurrentArtwork(BaseRatingDataModel):
    """当前进行分级的作品"""
    aid: str
    source_path: str


class CustomImportArtwork(BaseRatingDataModel):
    """导出后供手动导入/更新的作品信息"""
    origin: str
    aid: str
    classification: int = Field(ge=-2, le=4)
    rating: int = Field(ge=-1, le=3)


__all__ = [
    'CurrentArtwork',
    'CustomImportArtwork',
]
