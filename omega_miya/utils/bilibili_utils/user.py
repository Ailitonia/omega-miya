from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result
from .request_utils import BiliRequestUtils
from .data_classes import BiliInfo, BiliResult


class BiliUser(object):
    __USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
    __DYNAMIC_API_URL = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history'

    def __init__(self, user_id: int):
        self.user_id = user_id

    @property
    def uid(self):
        return self.user_id

    @property
    def mid(self):
        return str(self.user_id)

    async def get_info(self) -> BiliResult.UserInfoInfoResult:
        cookies = None
        # 检查cookies
        cookies_res = BiliRequestUtils.get_cookies()
        if cookies_res.success():
            cookies = cookies_res.result

        paras = {'mid': self.mid}
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
                    user_id=self.user_id,
                    name=user_info['data']['name'],
                    sex=user_info['data']['sex'],
                    face=user_info['data']['face'],
                    sign=user_info['data']['sign'],
                    level=user_info['data']['level'],
                )
                return BiliResult.UserInfoInfoResult(error=False, info='Success', result=result)
            except Exception as e:
                return BiliResult.UserInfoInfoResult(error=True, info=f'User info parse failed: {repr(e)}', result=None)

    async def get_dynamic_history(self) -> Result.DictListResult:
        __HEADERS = BiliRequestUtils.HEADERS.copy()
        __HEADERS.update({'origin': 'https://t.bilibili.com',
                          'referer': 'https://t.bilibili.com/'})

        cookies = None
        # 检查cookies
        cookies_res = BiliRequestUtils.get_cookies()
        if cookies_res.success():
            cookies = cookies_res.result

        bili_uid = BiliRequestUtils.get_bili_uid()
        bili_csrf = BiliRequestUtils.get_bili_csrf()
        if bili_uid and bili_csrf:
            paras = {'csrf': bili_csrf, 'visitor_uid': bili_uid, 'host_uid': self.user_id,
                     'offset_dynamic_id': 0, 'need_top': 0, 'platform': 'web'}
        else:
            paras = {'host_uid': self.user_id, 'offset_dynamic_id': 0, 'need_top': 0, 'platform': 'web'}

        fetcher = HttpFetcher(timeout=10, flag='bilibili_live', headers=__HEADERS, cookies=cookies)
        result = await fetcher.get_json(url=self.__DYNAMIC_API_URL, params=paras)

        if result.error:
            return result

        if result.result.get('code') != 0:
            return Result.DictListResult(error=True, info=result.result.get('message'), result=[])

        try:
            if not result.result['data'].get('cards'):
                return Result.DictListResult(error=False, info='Success. But user has no dynamic.', result=[])
            data_list = [dict(card) for card in result.result['data']['cards']]
            return Result.DictListResult(error=False, info='Success', result=data_list)
        except Exception as e:
            return Result.DictListResult(error=True, info=repr(e), result=[])


__all__ = [
    'BiliUser'
]
