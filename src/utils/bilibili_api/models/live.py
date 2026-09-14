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
    area_id: int = Field(default=-1)
    area_name: str = Field(default='直播')
    parent_area_id: int = Field(default=-1)
    parent_area_name: str = Field(default='直播')
    live_status: LiveStatus
    live_time: datetime | str = Field(default_factory=datetime.now, union_mode='left_to_right')
    uname: str = Field(default='bilibili用户')
    title: str
    description: str = Field(default='', exclude=True)
    tags: str = Field(default='', exclude=True)
    attention: int = Field(default=-1)
    online: int = Field(default=-1, exclude=True)
    live_url: AnyHttpUrl | str = Field(default='', exclude=True)
    cover: AnyHttpUrl | str = Field(default='', exclude=True)
    user_cover: AnyHttpUrl | str = Field(default='', exclude=True)
    cover_from_user: AnyHttpUrl | str = Field(default='', exclude=True)

    @property
    def cover_url(self) -> str:
        return self.cover or self.user_cover or self.cover_from_user

    @field_validator('live_time', mode='after')
    @classmethod
    def time_zone_conversion(cls, v):
        if isinstance(v, datetime):
            if v.tzinfo is None:
                # bilibili 返回的开播时间为东八区本地时间, naive datetime 应直接按本地时区解释,
                # 而非 astimezone 默认的服务器系统时区 (pytz 时区须用 localize 附加, 不能用 replace)
                v = DEFAULT_LOCAL_TZ.localize(v)
            else:
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
