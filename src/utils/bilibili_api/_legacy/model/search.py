"""
@Author         : Ailitonia
@Date           : 2022/04/11 21:35
@FileName       : search.py
@Project        : nonebot2_miya 
@Description    : Bilibili Searching Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import Field

from .base_model import BaseBilibiliModel


class BaseBilibiliSearchingDataModel[T](BaseBilibiliModel):
    """Bilibili 搜索结果 Data 基类"""
    cost_time: dict
    egg_hit: int
    exp_list: dict | None = None
    numPages: int
    numResults: int
    page: int
    pagesize: int
    rqt_type: str
    seid: str
    show_column: int
    suggest_keyword: str
    result: list[T] = Field(default_factory=list)


class BaseBilibiliSearchingModel[T: BaseBilibiliSearchingDataModel](BaseBilibiliModel):
    """Bilibili 搜索结果 Model 基类"""
    code: int
    data: T | None = None
    message: str

    @property
    def error(self) -> bool:
        return self.code != 0

    @property
    def results(self) -> list[T]:
        if self.data is None:
            return []
        return [x for x in self.data.result]


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
    verify_info: str | None = None


class UserSearchingData(BaseBilibiliSearchingDataModel[UserSearchingResult]):
    """用户搜索 Data"""
    result: list[UserSearchingResult] = Field(default_factory=list)


class UserSearchingModel(BaseBilibiliSearchingModel[UserSearchingData]):
    """用户搜索 Model"""
    data: UserSearchingData | None = None


__all__ = [
    'BaseBilibiliSearchingModel',
    'UserSearchingModel',
]
