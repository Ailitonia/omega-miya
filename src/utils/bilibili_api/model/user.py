"""
@Author         : Ailitonia
@Date           : 2022/04/11 20:37
@FileName       : user.py
@Project        : nonebot2_miya 
@Description    : Bilibili User Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Optional

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel


class BilibiliUserLiveRoom(BaseBilibiliModel):
    """Bilibili 用户直播间"""
    roomStatus: int
    liveStatus: int
    url: AnyHttpUrl
    title: str
    cover: AnyHttpUrl
    roomid: int
    roundStatus: int
    broadcast_type: int


class BilibiliUserDataModel(BaseBilibiliModel):
    """Bilibili 用户信息"""
    mid: int
    name: str
    sex: str
    face: AnyHttpUrl
    sign: str
    level: int
    top_photo: AnyHttpUrl
    live_room: Optional[BilibiliUserLiveRoom] = None
    is_senior_member: int


class BilibiliUserModel(BaseBilibiliModel):
    """Bilibili 用户 Model"""
    code: int
    data: Optional[BilibiliUserDataModel] = None
    message: str

    @property
    def error(self) -> bool:
        return self.code != 0

    @property
    def mid(self) -> int:
        return self.data.mid  # type: ignore

    @property
    def uname(self) -> str:
        return self.data.name  # type: ignore

    @property
    def live_room(self) -> BilibiliUserLiveRoom:
        return self.data.live_room  # type: ignore


__all__ = [
    'BilibiliUserModel'
]
