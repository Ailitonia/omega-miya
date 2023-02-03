"""
@Author         : Ailitonia
@Date           : 2022/04/11 21:35
@FileName       : search.py
@Project        : nonebot2_miya 
@Description    : Bilibili Searching Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Generic, Generator, TypeVar, Any, Optional
from pydantic.generics import GenericModel
from .base_model import BaseBilibiliModel


T = TypeVar("T")


class BaseBilibiliSearchingDataModel(BaseBilibiliModel, GenericModel, Generic[T]):
    """Bilibili 搜索结果 Data 基类"""
    cost_time: dict
    egg_hit: int
    exp_list: Optional[dict]
    numPages: int
    numResults: int
    page: int
    pagesize: int
    rqt_type: str
    seid: str
    show_column: int
    suggest_keyword: str
    result: list[T] = []


class BaseBilibiliSearchingModel(BaseBilibiliModel, GenericModel, Generic[T]):
    """Bilibili 搜索结果 Model 基类"""
    code: int
    data: Optional[BaseBilibiliSearchingDataModel[T]]
    message: str

    @property
    def error(self) -> bool:
        return self.code != 0

    @property
    def results(self) -> Generator[T, Any, None]:
        if self.data is None:
            return
        for result in self.data.result:
            yield result


class UserSearchingResult(BaseBilibiliModel):
    """用户搜索结果"""
    type: str
    uname: str
    upic: str
    usign: str
    mid: int
    room_id: int
    is_live: int
    level: int
    videos: int
    fans: int
    verify_info: str | None


class UserSearchingData(BaseBilibiliSearchingDataModel[UserSearchingResult]):
    """用户搜索 Data"""
    result: list[UserSearchingResult]


class UserSearchingModel(BaseBilibiliSearchingModel[UserSearchingResult]):
    """用户搜索 Model"""
    data: Optional[UserSearchingData]


__all__ = [
    'BaseBilibiliSearchingModel',
    'UserSearchingModel'
]
