"""
@Author         : Ailitonia
@Date           : 2024/12/24 14:09:35
@FileName       : live.py
@Project        : omega-miya
@Description    : live models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from datetime import datetime
from enum import IntEnum, unique

from pydantic import Field, field_validator

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel, BaseBilibiliResponse
from ..consts import DEFAULT_LOCAL_TZ


@unique
class LiveStatus(IntEnum):
    offline = 0  # 未开播
    streaming = 1  # 正在直播
    rotating = 2  # 轮播中


class RoomInfoData(BaseBilibiliModel):
    uid: int
    room_id: int
    short_id: int
    live_status: LiveStatus
    live_time: datetime | str = Field(default_factory=datetime.now)
    title: str
    description: str = Field('')
    user_cover: AnyHttpUrl | str = Field('')
    cover_from_user: AnyHttpUrl | str = Field('')

    @property
    def cover_url(self) -> str:
        return str(self.user_cover if self.user_cover else self.cover_from_user)

    @field_validator('live_time', mode='after')
    @classmethod
    def time_zone_conversion(cls, v):
        if isinstance(v, datetime):
            v = v.astimezone(DEFAULT_LOCAL_TZ)
        return v


class RoomInfo(BaseBilibiliResponse):
    data: RoomInfoData


class UsersRoomInfo(BaseBilibiliResponse):
    data: dict[int, RoomInfoData]


class UserDataInfo(BaseBilibiliModel):
    uid: int
    uname: str
    face: str
    rank: str
    gender: int


class RoomUserData(BaseBilibiliModel):
    info: UserDataInfo
    # level: dict[str, Any]
    san: int


class RoomUserInfo(BaseBilibiliResponse):
    data: RoomUserData


__all__ = [
    'RoomInfo',
    'RoomUserInfo',
    'UsersRoomInfo',
]
