from typing import List, Union
import datetime
from nonebot import logger
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from .request_utils import BiliRequestUtils
from .data_classes import BiliInfo, BiliResult


class BiliLiveRoom(object):
    __LIVE_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_info'
    __LIVE_BY_UIDS_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
    __USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
    __LIVE_URL = 'https://live.bilibili.com/'

    def __init__(self, room_id: int):
        self.room_id = room_id

    @property
    def rid(self):
        return str(self.room_id)

    async def get_info(self) -> BiliResult.LiveRoomInfoResult:
        cookies = None
        # 检查cookies
        cookies_res = BiliRequestUtils.get_cookies()
        if cookies_res.success():
            cookies = cookies_res.result

        paras = {'id': self.rid}
        fetcher = HttpFetcher(
            timeout=10, flag='bilibili_live', headers=BiliRequestUtils.HEADERS, cookies=cookies)
        result = await fetcher.get_json(url=self.__LIVE_API_URL, params=paras)

        if not result.success():
            return BiliResult.LiveRoomInfoResult(error=True, info=result.info, result=None)
        elif result.result.get('code') != 0:
            return BiliResult.LiveRoomInfoResult(
                error=True, info=f"Get Live info failed: {result.result.get('message')}", result=None)
        else:
            live_info = result.result
            try:
                result = BiliInfo.LiveRoomInfo(
                    room_id=self.room_id,
                    short_id=live_info['data']['short_id'],
                    user_id=live_info['data']['uid'],
                    status=live_info['data']['live_status'],
                    url=f'{self.__LIVE_URL}{self.room_id}',
                    title=live_info['data']['title'],
                    live_time=live_info['data']['live_time'],
                    cover_img=live_info['data']['user_cover']
                )
                return BiliResult.LiveRoomInfoResult(error=False, info='Success', result=result)
            except Exception as e:
                return BiliResult.LiveRoomInfoResult(error=True, info=f'Live info parse failed: {repr(e)}', result=None)

    @classmethod
    async def get_info_by_uids(cls, uid_list: List[Union[int, str]]) -> BiliResult.LiveRoomDictInfoResult:
        """
        :param uid_list: uid 列表
        :return: result: {直播间房间号: 直播间信息}
        """
        payload = {'uids': uid_list}
        fetcher = HttpFetcher(
            timeout=10, flag='bilibili_live_list_users_live', headers=BiliRequestUtils.HEADERS)
        api_result = await fetcher.post_json(url=cls.__LIVE_BY_UIDS_API_URL, json=payload)
        if api_result.error:
            return BiliResult.LiveRoomDictInfoResult(error=True, info=api_result.info, result=None)

        api_code = api_result.result.get('code')
        api_msg = api_result.result.get('message')
        if api_code != 0:
            return BiliResult.LiveRoomDictInfoResult(error=True, info=f'Api error: {api_msg}', result=None)

        result = {}
        live_data = dict(api_result.result.get('data'))
        for uid, room_info in live_data.items():
            try:
                result.update({
                    int(room_info.get('room_id')): BiliInfo.LiveRoomInfo(
                        room_id=room_info.get('room_id'),
                        short_id=room_info.get('short_id'),
                        user_id=int(uid),
                        status=room_info.get('live_status'),
                        url=f"{cls.__LIVE_URL}{room_info.get('room_id')}",
                        title=room_info.get('title'),
                        live_time=datetime.datetime.fromtimestamp(room_info.get('live_time')).strftime(
                            '%Y-%m-%d %H:%M:%S'),
                        cover_img=room_info.get('cover_from_user'))
                })
            except Exception as e:
                logger.error(f'BiliLiveRoom: parse room live info failed, uid: {uid}, error info: {repr(e)}')
                continue
        return BiliResult.LiveRoomDictInfoResult(error=False, info='Success', result=result)

    async def get_user_info(self) -> BiliResult.UserInfoInfoResult:
        room_info_result = await self.get_info()
        if room_info_result.error:
            return BiliResult.UserInfoInfoResult(error=True, info=room_info_result.info, result=None)

        cookies = None
        # 检查cookies
        cookies_res = BiliRequestUtils.get_cookies()
        if cookies_res.success():
            cookies = cookies_res.result

        paras = {'mid': room_info_result.result.mid}
        fetcher = HttpFetcher(
            timeout=10, flag='bilibili_live', headers=BiliRequestUtils.HEADERS, cookies=cookies)
        result = await fetcher.get_json(url=self.__USER_INFO_API_URL, params=paras)

        if not result.success():
            return BiliResult.UserInfoInfoResult(error=True, info=result.info, result=None)
        elif result.result.get('code') != 0:
            return BiliResult.UserInfoInfoResult(
                error=True, info=f"Get User info failed: {result.result.get('message')}", result=None)
        else:
            user_info = result.result
            try:
                result = BiliInfo.UserInfo(
                    user_id=room_info_result.result.user_id,
                    name=user_info['data']['name'],
                    sex=user_info['data']['sex'],
                    face=user_info['data']['face'],
                    sign=user_info['data']['sign'],
                    level=user_info['data']['level'],
                )
                return BiliResult.UserInfoInfoResult(error=False, info='Success', result=result)
            except Exception as e:
                return BiliResult.UserInfoInfoResult(error=True, info=f'User info parse failed: {repr(e)}', result=None)


__all__ = [
    'BiliLiveRoom'
]
