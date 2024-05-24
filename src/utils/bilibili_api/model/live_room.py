"""
@Author         : Ailitonia
@Date           : 2022/04/12 21:23
@FileName       : live_room.py
@Project        : nonebot2_miya 
@Description    : Bilibili Live Room Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from pydantic import field_validator
from pytz import timezone
from typing import Optional

from src.compat import AnyHttpUrlStr as AnyHttpUrl

from .base_model import BaseBilibiliModel


_DEFAULT_LOCAL_TZ = timezone('Asia/Shanghai')
"""默认本地时区"""


class BilibiliLiveRoomDataModel(BaseBilibiliModel):
    """Bilibili 直播间 Data Model"""
    uid: int
    room_id: int
    short_id: int
    title: str
    live_status: int
    live_time: datetime | str
    user_cover: AnyHttpUrl | str = ''
    cover_from_user: AnyHttpUrl | str = ''
    description: str = ''

    @property
    def cover(self) -> str:
        return str(self.user_cover if self.user_cover else self.cover_from_user)

    @field_validator('live_time')
    @classmethod
    def time_zone_conversion(cls, v):
        if isinstance(v, datetime):
            v = v.astimezone(_DEFAULT_LOCAL_TZ)
        return v


class BilibiliLiveRoomModel(BaseBilibiliModel):
    """Bilibili 直播间 Model"""
    code: int
    data: Optional[BilibiliLiveRoomDataModel] = None
    msg: str = ''
    message: str = ''

    @property
    def error(self) -> bool:
        return self.code != 0

    @property
    def uid(self) -> int:
        return self.data.uid


class BilibiliUsersLiveRoomModel(BaseBilibiliModel):
    """通过批量查询用户直播间 api 查询到的直播间 Model"""
    code: int
    data: dict[int, BilibiliLiveRoomDataModel]
    msg: str = ''
    message: str = ''

    @property
    def error(self) -> bool:
        return self.code != 0


__all__ = [
    'BilibiliLiveRoomDataModel',
    'BilibiliLiveRoomModel',
    'BilibiliUsersLiveRoomModel'
]
