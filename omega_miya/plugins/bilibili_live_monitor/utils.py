import nonebot
from omega_miya.utils.Omega_Base import Result
from omega_miya.utils.Omega_plugin_utils import HttpFetcher, PicEncoder

LIVE_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_info'
USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
LIVE_URL = 'https://live.bilibili.com/'

global_config = nonebot.get_driver().config
BILI_SESSDATA = global_config.bili_sessdata
BILI_CSRF = global_config.bili_csrf
BILI_UID = global_config.bili_uid
ENABLE_BILI_CHECK_POOL_MODE = global_config.enable_bili_check_pool_mode


def check_bili_cookies() -> Result:
    cookies = {}
    if BILI_SESSDATA and BILI_CSRF:
        cookies.update({'SESSDATA': BILI_SESSDATA})
        cookies.update({'bili_jct': BILI_CSRF})
        return Result(error=False, info='Success', result=cookies)
    else:
        return Result(error=True, info='None', result=cookies)


async def fetch_json(url: str, paras: dict = None) -> HttpFetcher.FetcherJsonResult:
    cookies = None

    # 检查cookies
    cookies_res = check_bili_cookies()
    if cookies_res.success():
        cookies = cookies_res.result

    headers = {'accept': 'application/json, text/plain, */*',
               'accept-encoding': 'gzip, deflate',
               'accept-language:': 'zh-CN,zh;q=0.9',
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

    fetcher = HttpFetcher(timeout=10, flag='bilibili_live_monitor', headers=headers, cookies=cookies)
    result = await fetcher.get_json(url=url, params=paras)
    return result


# 图片转base64
async def pic_2_base64(url: str) -> Result:
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                             'Chrome/89.0.4389.114 Safari/537.36',
               'origin': 'https://www.bilibili.com',
               'referer': 'https://www.bilibili.com/'}

    fetcher = HttpFetcher(
        timeout=30, attempt_limit=2, flag='bilibili_live_monitor_get_image', headers=headers)
    bytes_result = await fetcher.get_bytes(url=url)
    if bytes_result.error:
        return Result(error=True, info='Image download failed', result='')

    encode_result = PicEncoder.bytes_to_b64(image=bytes_result.result)

    if encode_result.success():
        return Result(error=False, info='Success', result=encode_result.result)
    else:
        return Result(error=True, info=encode_result.info, result='')


# 获取直播间信息
async def get_live_info(room_id) -> Result:
    url = LIVE_API_URL
    payload = {'id': room_id}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    elif result.result.get('code') != 0:
        result = Result(error=True, info=f"Get Live info failed: {result.result.get('message')}", result={})
    else:
        live_info = result.result
        try:
            _res = {
                'status': live_info['data']['live_status'],
                'url': LIVE_URL + str(room_id),
                'title': live_info['data']['title'],
                'time': live_info['data']['live_time'],
                'uid': live_info['data']['uid'],
                'cover_img': live_info['data']['user_cover']
            }
            result = Result(error=False, info='Success', result=_res)
        except Exception as e:
            result = Result(error=True, info=f'Live info parse failed: {repr(e)}', result={})
    return result


# 根据用户uid获取用户信息
async def get_user_info(user_uid) -> Result:
    url = USER_INFO_API_URL
    payload = {'mid': user_uid}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    elif result.result.get('code') != 0:
        result = Result(error=True, info=f"Get User info failed: {result.result.get('message')}", result={})
    else:
        user_info = result.result
        try:
            _res = {
                'status': user_info['code'],
                'name': user_info['data']['name']
            }
            result = Result(error=False, info='Success', result=_res)
        except Exception as e:
            result = Result(error=True, info=f'User info parse failed: {repr(e)}', result={})
    return result


async def verify_cookies() -> Result:
    cookies_verify_url = 'https://api.bilibili.com/x/web-interface/nav'
    _res = await fetch_json(url=cookies_verify_url, paras=None)
    if _res.success():
        code = _res.result.get('code')
        data = dict(_res.result.get('data'))
        if code == 0 and data.get('isLogin'):
            uname = data.get('uname')
            mid = data.get('mid')
            if mid == BILI_UID:
                result = Result(error=False, info='Success login', result=uname)
            else:
                result = Result(error=True, info='Logged user UID does not match', result=uname)
        else:
            result = Result(error=True, info='Not login', result='')
        return result
    else:
        return _res


__all__ = [
    'get_live_info',
    'get_user_info',
    'pic_2_base64',
    'verify_cookies',
    'ENABLE_BILI_CHECK_POOL_MODE'
]
