"""
@Author         : Ailitonia
@Date           : 2024/11/15 16:19:17
@FileName       : user.py
@Project        : omega-miya
@Description    : user models
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from pydantic import Field

from src.compat import AnyHttpUrlStr as AnyHttpUrl
from .base_model import BaseBilibiliModel, BaseBilibiliResponse


class AccountData(BaseBilibiliModel):
    mid: int
    uname: str
    userid: str
    sign: str
    birthday: str
    sex: str
    nick_free: bool
    rank: str


class Account(BaseBilibiliResponse):
    """api.bilibili.com/x/member/web/account 返回值"""
    data: AccountData


class VipData(BaseBilibiliModel):
    mid: int
    vip_type: int
    vip_status: int
    vip_due_date: int
    vip_pay_type: int
    theme_type: int


class VipInfo(BaseBilibiliResponse):
    data: VipData


class UserOfficial(BaseBilibiliModel):
    role: int
    title: str
    desc: str
    type: int


class UserLiveRoom(BaseBilibiliModel):
    room_status: int = Field(alias='roomStatus')
    live_status: int = Field(alias='liveStatus')
    url: AnyHttpUrl
    title: str
    cover: AnyHttpUrl
    roomid: int
    round_status: int = Field(alias='roundStatus')
    broadcast_type: int


class UserData(BaseBilibiliModel):
    mid: int
    name: str
    sex: str
    face: AnyHttpUrl
    sign: str
    rank: int
    level: int
    jointime: int
    moral: int
    silence: int
    coins: int
    official: UserOfficial
    is_followed: bool
    top_photo: AnyHttpUrl
    live_room: UserLiveRoom
    birthday: str


class User(BaseBilibiliResponse):
    """api.bilibili.com/x/space/wbi/acc/info 返回值"""
    data: UserData

    @property
    def mid(self) -> int:
        return self.data.mid

    @property
    def uname(self) -> str:
        return self.data.name

    @property
    def live_room(self) -> UserLiveRoom:
        return self.data.live_room


class UserSpaceRenderData(BaseBilibiliModel):
    """space.bilibili.com 页面 __RENDER_DATA__ 元素内容"""
    access_id: str


__all__ = [
    'Account',
    'User',
    'UserLiveRoom',
    'UserSpaceRenderData',
    'VipInfo',
]
