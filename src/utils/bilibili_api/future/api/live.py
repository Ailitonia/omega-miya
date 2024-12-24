"""
@Author         : Ailitonia
@Date           : 2024/12/24 14:01:52
@FileName       : live.py
@Project        : omega-miya
@Description    : bilibili 直播相关 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Sequence

from .base import BilibiliCommon
from ..models import RoomBaseInfo, RoomInfo, RoomUserInfo, UsersRoomInfo


class BilibiliLive(BilibiliCommon):
    """Bilibili 直播 API"""

    @classmethod
    async def query_room_info(cls, room_id: int | str) -> RoomInfo:
        """获取直播间信息"""
        url = 'https://api.live.bilibili.com/room/v1/Room/get_info'
        params = {'room_id': str(room_id)}
        data = await cls._get_json(url=url, params=params)
        return RoomInfo.model_validate(data)

    @classmethod
    async def query_room_info_by_room_id_list(cls, room_id_list: Sequence[int | str]) -> RoomBaseInfo:
        """根据直播间房间号列表获取这些直播间的信息"""
        url = 'https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo'
        params = (('req_biz', 'web_room_componet'), *(('room_ids', str(x)) for x in room_id_list))
        data = await cls._get_json(url=url, params=list(params))
        return RoomBaseInfo.model_validate(data)

    @classmethod
    async def query_room_info_by_uid_list(cls, uid_list: Sequence[int | str]) -> UsersRoomInfo:
        """根据用户 uid 列表获取这些用户的直播间信息(这个 api 没有认证方法，请不要在标头中添加 cookie)"""
        url = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
        payload = {'uids': uid_list}
        # 该接口无需鉴权
        data = await cls._post_json(url=url, json=payload, no_headers=True, no_cookies=True)
        return UsersRoomInfo.model_validate(data)

    @classmethod
    async def query_room_user_info(cls, room_id: int | str) -> RoomUserInfo:
        """获取直播间对应的主播信息"""
        url = 'https://api.live.bilibili.com/live_user/v1/UserInfo/get_anchor_in_room'
        params = {'roomid': str(room_id)}
        data = await cls._get_json(url=url, params=params)
        return RoomUserInfo.model_validate(data)


__all__ = [
    'BilibiliLive',
]
