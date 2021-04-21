import nonebot
import datetime
from typing import List, Union
from nonebot.log import logger
from omega_miya.utils.Omega_Base import Result
from omega_miya.utils.Omega_plugin_utils import HttpFetcher, PicEncoder
from .config import Config

LIVE_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_info'
LIVE_BY_UIDS_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids'
USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
LIVE_URL = 'https://live.bilibili.com/'

global_config = nonebot.get_driver().config
plugin_config = Config(**global_config.dict())
BILI_SESSDATA = global_config.bili_sessdata
BILI_CSRF = global_config.bili_csrf
BILI_UID = global_config.bili_uid
ENABLE_NEW_LIVE_API = plugin_config.enable_new_live_api
ENABLE_LIVE_CHECK_POOL_MODE = plugin_config.enable_live_check_pool_mode

HEADERS = {'accept': 'application/json, text/plain, */*',
           'accept-encoding': 'gzip, deflate',
           'accept-language': 'zh-CN,zh;q=0.9',
           'dnt': '1',
           'origin': 'https://www.bilibili.com',
           'referer': 'https://www.bilibili.com/',
           'sec-ch-ua': '"Google Chrome";v="89", "Chromium";v="89", ";Not A Brand";v="99"',
           'sec-ch-ua-mobile': '?0',
           'sec-fetch-dest': 'empty',
           'sec-fetch-mode': 'cors',
           'sec-fetch-site': 'same-site',
           'sec-gpc': '1',
           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/89.0.4389.114 Safari/537.36'
           }


def check_bili_cookies() -> Result.DictResult:
    cookies = {}
    if BILI_SESSDATA and BILI_CSRF:
        cookies.update({'SESSDATA': BILI_SESSDATA})
        cookies.update({'bili_jct': BILI_CSRF})
        return Result.DictResult(error=False, info='Success', result=cookies)
    else:
        return Result.DictResult(error=True, info='None', result=cookies)


async def fetch_json(url: str, paras: dict = None) -> HttpFetcher.FetcherJsonResult:
    cookies = None

    # 检查cookies
    cookies_res = check_bili_cookies()
    if cookies_res.success():
        cookies = cookies_res.result

    fetcher = HttpFetcher(timeout=10, flag='bilibili_live_monitor', headers=HEADERS, cookies=cookies)
    result = await fetcher.get_json(url=url, params=paras)
    return result


# 图片转base64
async def pic_2_base64(url: str) -> Result.TextResult:
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36',
               'origin': 'https://www.bilibili.com',
               'referer': 'https://www.bilibili.com/'}

    fetcher = HttpFetcher(
        timeout=30, attempt_limit=2, flag='bilibili_live_monitor_get_image', headers=headers)
    bytes_result = await fetcher.get_bytes(url=url)
    if bytes_result.error:
        return Result.TextResult(error=True, info='Image download failed', result='')

    encode_result = PicEncoder.bytes_to_b64(image=bytes_result.result)

    if encode_result.success():
        return Result.TextResult(error=False, info='Success', result=encode_result.result)
    else:
        return Result.TextResult(error=True, info=encode_result.info, result='')


# 获取直播间信息
async def get_live_info(room_id) -> Result.DictResult:
    url = LIVE_API_URL
    payload = {'id': room_id}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    elif result.result.get('code') != 0:
        result = Result.DictResult(error=True, info=f"Get Live info failed: {result.result.get('message')}", result={})
    else:
        live_info = result.result
        try:
            _res = {
                'status': live_info['data']['live_status'],
                'url': LIVE_URL + str(room_id),
                'title': live_info['data']['title'],
                'time': live_info['data']['live_time'],
                'uid': live_info['data']['uid'],
                'cover_img': live_info['data']['user_cover'],
                'room_id': live_info['data']['room_id'],
                'short_id': live_info['data']['short_id']
            }
            result = Result.DictResult(error=False, info='Success', result=_res)
        except Exception as e:
            result = Result.DictResult(error=True, info=f'Live info parse failed: {repr(e)}', result={})
    return result


# 获取直播间信息
async def get_live_info_by_uid_list(uid_list: List[Union[int, str]]) -> Result.DictResult:
    """
    :param uid_list: uid 列表
    :return: result: {直播间房间号: 直播间信息}
    """
    payload = {'uids': uid_list}

    fetcher = HttpFetcher(timeout=10, flag='bilibili_live_monitor_list_users_live', headers=HEADERS)
    api_result = await fetcher.post_json(url=LIVE_BY_UIDS_API_URL, json=payload)

    if api_result.error:
        return Result.DictResult(error=True, info=api_result.info, result={})

    api_code = api_result.result.get('code')
    api_msg = api_result.result.get('message')
    if api_code != 0:
        return Result.DictResult(error=True, info=f'Api error: {api_msg}', result={})

    result = {}
    live_data = dict(api_result.result.get('data'))
    for uid, room_info in live_data.items():
        try:
            result.update({
                int(room_info.get('room_id')): {
                    'status': room_info.get('live_status'),
                    'url': LIVE_URL + str(room_info.get('room_id')),
                    'title': room_info.get('title'),
                    'time': datetime.datetime.fromtimestamp(room_info.get('live_time')).strftime('%Y-%m-%d %H:%M:%S'),
                    'uid': int(uid),
                    'cover_img': room_info.get('cover_from_user'),
                    'room_id': room_info.get('room_id'),
                    'short_id': room_info.get('short_id')
                }
            })
        except Exception as e:
            logger.warning(f'bilibili_live_monitor_utils: parse room live info failed, error info: {repr(e)}')
            continue
    return Result.DictResult(error=False, info='Success', result=result)


# 根据用户uid获取用户信息
async def get_user_info(user_uid) -> Result.DictResult:
    url = USER_INFO_API_URL
    payload = {'mid': user_uid}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    elif result.result.get('code') != 0:
        result = Result.DictResult(error=True, info=f"Get User info failed: {result.result.get('message')}", result={})
    else:
        user_info = result.result
        try:
            _res = {
                'status': user_info['code'],
                'name': user_info['data']['name']
            }
            result = Result.DictResult(error=False, info='Success', result=_res)
        except Exception as e:
            result = Result.DictResult(error=True, info=f'User info parse failed: {repr(e)}', result={})
    return result


async def verify_cookies() -> Result.TextResult:
    cookies_verify_url = 'https://api.bilibili.com/x/web-interface/nav'
    _res = await fetch_json(url=cookies_verify_url, paras=None)
    if _res.success():
        code = _res.result.get('code')
        data = dict(_res.result.get('data'))
        if code == 0 and data.get('isLogin'):
            uname = data.get('uname')
            mid = data.get('mid')
            if mid == BILI_UID:
                result = Result.TextResult(error=False, info='Success login', result=uname)
            else:
                result = Result.TextResult(error=True, info='Logged user UID does not match', result=uname)
        else:
            result = Result.TextResult(error=True, info='Not login', result='')
        return result
    else:
        return Result.TextResult(error=True, info=_res.info, result='')


__all__ = [
    'get_live_info',
    'get_live_info_by_uid_list',
    'get_user_info',
    'pic_2_base64',
    'verify_cookies',
    'ENABLE_NEW_LIVE_API',
    'ENABLE_LIVE_CHECK_POOL_MODE'
]
