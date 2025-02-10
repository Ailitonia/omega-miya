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
    uid: str
    room_id: str
    short_id: str
    live_status: LiveStatus
    live_time: datetime | str = Field(default_factory=datetime.now)
    uname: str = Field('bilibili用户')
    title: str
    description: str = Field('')
    cover: AnyHttpUrl | str = Field('')
    user_cover: AnyHttpUrl | str = Field('')
    cover_from_user: AnyHttpUrl | str = Field('')

    @property
    def cover_url(self) -> str:
        return self.cover or self.user_cover or self.cover_from_user

    @field_validator('live_time', mode='after')
    @classmethod
    def time_zone_conversion(cls, v):
        if isinstance(v, datetime):
            v = v.astimezone(DEFAULT_LOCAL_TZ)
        return v


class RoomBaseInfoData(BaseBilibiliModel):
    # by_uids: dict[str, Any]
    by_room_ids: dict[str, RoomInfoData]


class RoomBaseInfo(BaseBilibiliResponse):
    data: RoomBaseInfoData


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
    'LiveStatus',
    'RoomBaseInfo',
    'RoomInfo',
    'RoomInfoData',
    'RoomUserInfo',
    'UsersRoomInfo',
]
