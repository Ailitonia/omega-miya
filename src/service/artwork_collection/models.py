"""
@Author         : Ailitonia
@Date           : 2024/6/11 上午1:54
@FileName       : models
@Project        : nonebot2_miya
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.compat import AnyHttpUrlStr as AnyHttpUrl


class BaseArtwork(BaseModel):
    """作品信息基类"""

    model_config = ConfigDict(extra='ignore', from_attributes=True, coerce_numbers_to_str=True, frozen=True)


class CollectedArtwork(BaseArtwork):
    """标准作品信息"""
    aid: str
    title: str
    uname: str
    tags: list[str]
    url: AnyHttpUrl

    @property
    @abc.abstractmethod
    def source(self) -> str:
        """注明作品原始来源"""
        raise NotImplementedError


class BaseArtworkCollection(abc.ABC):
    """作品合集基类, 封装后用于插件调用的数据库实体操作对象"""

    def __init__(self, artwork_id: str):
        self.artwork_id = artwork_id

    @property
    @abc.abstractmethod
    def source(self) -> str:
        """注明合集原始来源"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def query_by_condition(
            cls,
            keywords: Optional[str | list[str]],
            num: Optional[int],
            *args,
            **kwargs
    ) -> list[CollectedArtwork]:
        """根据要求查询作品"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    async def random(
            cls,
            num: Optional[int],
            *args,
            **kwargs
    ) -> list[CollectedArtwork]:
        """获取随机作品"""
        raise NotImplementedError

    @abc.abstractmethod
    async def query_artwork(self) -> CollectedArtwork:
        """获取作品信息"""
        raise NotImplementedError


__all__ = [
    'BaseArtwork',
    'BaseArtworkCollection',
    'CollectedArtwork'
]
