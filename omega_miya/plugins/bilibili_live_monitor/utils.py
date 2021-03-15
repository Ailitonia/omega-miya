import aiohttp
import nonebot
import base64
from io import BytesIO
from omega_miya.utils.Omega_Base import Result

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


async def fetch_json(url: str, paras: dict = None) -> Result:
    cookies = None
    cookies_res = check_bili_cookies()
    if cookies_res.success():
        cookies = cookies_res.result
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'accept': 'application/json, text/plain, */*',
                           'accept-encoding': 'gzip, deflate, br',
                           'accept-language:': 'zh-CN,zh;q=0.9',
                           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                           'origin': 'https://www.bilibili.com',
                           'referer': 'https://www.bilibili.com/'}
                async with session.get(url=url, params=paras, headers=headers, cookies=cookies, timeout=timeout) as rp:
                    _json = await rp.json()
                result = Result(error=False, info='Success', result=_json)
            return result
        except Exception as e:
            error_info += f'{repr(e)} Occurred in fetch_json trying {timeout_count + 1} using paras: {paras}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in fetch_json using paras: {paras}'
        result = Result(error=True, info=error_info, result={})
        return result


# 图片转base64
async def pic_2_base64(url: str) -> Result:
    async def get_image(pic_url: str):
        timeout_count = 0
        error_info = ''
        while timeout_count < 3:
            try:
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                               'origin': 'https://www.bilibili.com',
                               'referer': 'https://www.bilibili.com/'}
                    async with session.get(url=pic_url, headers=headers, timeout=timeout) as resp:
                        _res = await resp.read()
                return _res
            except Exception as _e:
                error_info += f'{repr(_e)} Occurred in pic_2_base64 trying {timeout_count + 1} using paras: {pic_url}\n'
            finally:
                timeout_count += 1
        else:
            error_info += f'Failed too many times in pic_2_base64 using paras: {pic_url}'
            return None

    origin_image_f = BytesIO()
    try:
        origin_image_f.write(await get_image(pic_url=url))
    except Exception as e:
        result = Result(error=True, info=f'pic_2_base64 error: {repr(e)}', result='')
        return result
    b64 = base64.b64encode(origin_image_f.getvalue())
    b64 = str(b64, encoding='utf-8')
    b64 = 'base64://' + b64
    origin_image_f.close()
    result = Result(error=False, info='Success', result=b64)
    return result


# 获取直播间信息
async def get_live_info(room_id) -> Result:
    url = LIVE_API_URL
    payload = {'id': room_id}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    elif dict(result.result).get('code') != 0:
        result = Result(error=True, info=f"Get Live info failed: {dict(result.result).get('message')}", result={})
    else:
        live_info = dict(result.result)
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
    elif dict(result.result).get('code') != 0:
        result = Result(error=True, info=f"Get User info failed: {dict(result.result).get('message')}", result={})
    else:
        user_info = dict(result.result)
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
