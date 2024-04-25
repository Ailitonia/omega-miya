"""
@Author         : Ailitonia
@Date           : 2024/4/25 上午12:20
@FileName       : model
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import BaseModel, ConfigDict

from src.compat import AnyUrlStr as AnyUrl


class BaseShindanMakerModel(BaseModel):
    """ShindanMaker 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True)


class ShindanMakerResult(BaseShindanMakerModel):
    """ShindanMaker 占卜结果"""
    text: str
    image_url: list[AnyUrl]


class ShindanMakerSearchResult(BaseShindanMakerModel):
    """ShindanMaker 搜索结果"""
    id: int
    name: str
    url: AnyUrl


__all__ = [
    'ShindanMakerResult',
    'ShindanMakerSearchResult'
]
