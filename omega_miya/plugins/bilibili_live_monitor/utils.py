import aiohttp
import nonebot
from omega_miya.utils.Omega_Base import Result

LIVE_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_info'
USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
LIVE_URL = 'https://live.bilibili.com/'

global_config = nonebot.get_driver().config
BILI_SESSDATA = global_config.bili_sessdata
BILI_CSRF = global_config.bili_csrf


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
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
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


# 获取直播间信息
async def get_live_info(room_id) -> Result:
    url = LIVE_API_URL
    payload = {'id': room_id}
    result = await fetch_json(url=url, paras=payload)
    if not result.success():
        return result
    else:
        live_info = dict(result.result)
        try:
            _res = {
                'status': live_info['data']['live_status'],
                'url': LIVE_URL + str(room_id),
                'title': live_info['data']['title'],
                'time': live_info['data']['live_time'],
                'uid': live_info['data']['uid']
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
            result = Result(error=False, info='Success login', result=uname)
        else:
            result = Result(error=True, info='Not login', result='')
        return result
    else:
        return _res


__all__ = [
    'get_live_info',
    'get_user_info',
    'verify_cookies'
]


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(verify_cookies())
    print(res)
