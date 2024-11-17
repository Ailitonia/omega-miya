"""
@Author         : Ailitonia
@Date           : 2022/05/03 19:45
@FileName       : model.py
@Project        : nonebot2_miya 
@Description    : Bilibili Dynamic Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class BilibiliLiveRoomStatus(BaseModel):
    """Bilibili 直播间状态"""
    live_room_id: int
    live_status: int
    live_title: str
    live_user_name: str

    def __eq__(self, other) -> bool:
        if isinstance(other, BilibiliLiveRoomStatus):
            return (
                self.live_room_id == other.live_room_id
                and self.live_status == other.live_status
                and self.live_title == other.live_title
            )
        else:
            return False

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __sub__(self, other) -> 'BilibiliLiveRoomStatusUpdate':
        if isinstance(other, BilibiliLiveRoomStatus):
            differ = set(self.model_dump().items()) - set(other.model_dump().items())
            differ_data = {k: v for k, v in differ}
            differ_data = None if not differ_data else differ_data
            return BilibiliLiveRoomStatusUpdate.model_validate({'is_update': self != other, 'update': differ_data})
        else:
            raise ValueError('BilibiliLiveRoomStatus can only be subtracted by the same class')


class BilibiliLiveRoomTitleChange(BaseModel):
    """Bilibili 直播间标题更新(仅标题更新, 直播间状态不变)

    - live_title: 更新后的直播间标题
    """
    live_title: str

    model_config = ConfigDict(extra='forbid')


class BilibiliLiveRoomStartLivingWithUpdateTitle(BaseModel):
    """Bilibili 直播间直播状态更新: 开播(同时更新标题)

    - live_title: 更新后的直播间标题
    - live_status: 更新后的直播状态
    """
    live_title: str
    live_status: Literal[1] = 1

    model_config = ConfigDict(extra='forbid')


class BilibiliLiveRoomStartLiving(BaseModel):
    """Bilibili 直播间直播状态更新: 开播(未更新标题)

    - live_status: 更新后的直播状态
    """
    live_status: Literal[1] = 1

    model_config = ConfigDict(extra='forbid')


class BilibiliLiveRoomStopLiving(BaseModel):
    """Bilibili 直播间直播状态更新: 下播

    - live_status: 更新后的直播状态
    """
    live_status: Literal[0] = 0

    model_config = ConfigDict(extra='ignore')


class BilibiliLiveRoomStopLivingWithPlaylist(BaseModel):
    """Bilibili 直播间直播状态更新: 下播后转轮播

    - live_status: 更新后的直播状态
    """
    live_status: Literal[2] = 2

    model_config = ConfigDict(extra='ignore')


class BilibiliLiveRoomStatusUpdate(BaseModel):
    """Bilibili 直播间状态更新"""
    is_update: bool
    update: BilibiliLiveRoomTitleChange | BilibiliLiveRoomStartLiving | BilibiliLiveRoomStartLivingWithUpdateTitle | BilibiliLiveRoomStopLiving | BilibiliLiveRoomStopLivingWithPlaylist | None = None

    @model_validator(mode='after')
    @classmethod
    def check_is_update(cls, values):
        is_update = values.is_update
        update = values.update
        if (is_update and update is None) or (not is_update and update is not None):
            raise ValueError('status update info do not match')
        return values


__all__ = [
    'BilibiliLiveRoomStatus',
    'BilibiliLiveRoomTitleChange',
    'BilibiliLiveRoomStartLiving',
    'BilibiliLiveRoomStartLivingWithUpdateTitle',
    'BilibiliLiveRoomStopLiving',
    'BilibiliLiveRoomStopLivingWithPlaylist',
    'BilibiliLiveRoomStatusUpdate',
]
