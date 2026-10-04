"""
@Author         : Ailitonia
@Date           : 2025/5/18 16:59
@FileName       : model
@Project        : omega-miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import BaseModel, ConfigDict, Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl


class BaseOsuWebModel(BaseModel):
    """osu! web 数据基类"""

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


class BeatMap(BaseOsuWebModel):
    id: str
    url: AnyHttpUrl
    name: str


class BeatmapsPack(BaseOsuWebModel):
    id: str
    download_url: AnyHttpUrl
    beatmaps: list[BeatMap] = Field(default_factory=list)


__all__ = [
    'BeatMap',
    'BeatmapsPack',
]
