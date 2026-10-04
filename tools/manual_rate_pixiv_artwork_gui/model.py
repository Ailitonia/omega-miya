"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:06
@FileName       : model
@Project        : ailitonia-toolkit
@Description    :
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict

type ALLOW_ARTWORK_ORIGIN = Literal[
    'pixiv',
    'danbooru',
    'gelbooru',
    'konachan',
    'yandere',
    'local_collected_artwork',
    'none',
]


class CustomImportArtwork(BaseModel):
    """手动导入/更新作品信息"""
    origin: ALLOW_ARTWORK_ORIGIN
    aid: str
    classification: int
    rating: int

    model_config = ConfigDict(extra='ignore', frozen=True, coerce_numbers_to_str=True)


__all__ = [
    'CustomImportArtwork',
]
