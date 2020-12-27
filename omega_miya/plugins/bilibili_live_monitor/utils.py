import aiohttp
from omega_miya.utils.Omega_Base import Result

LIVE_API_URL = 'https://api.live.bilibili.com/room/v1/Room/get_info'
USER_INFO_API_URL = 'https://api.bilibili.com/x/space/acc/info'
LIVE_URL = 'https://live.bilibili.com/'


async def fetch_json(url: str, paras: dict) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                           'referer': 'https://www.bilibili.com/'}
                async with session.get(url=url, params=paras, headers=headers, timeout=timeout) as resp:
                    _json = await resp.json()
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


__all__ = [
    'get_live_info',
    'get_user_info'
]


if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    res = loop.run_until_complete(get_live_info(room_id=3012597))
    print(res)
