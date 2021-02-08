import aiohttp
import nonebot
from omega_miya.utils.Omega_Base import Result


global_config = nonebot.get_driver().config
API_KEY = global_config.api_key
RANK_API_URL = f'{global_config.api_url}/api/pixiv/rank/'
SEARCH_API_URL = f'{global_config.api_url}/api/pixiv/search/'
DOWNLOAD_API_URL = f'{global_config.api_url}/api/pixiv/download/'


async def fetch_json(url: str, paras: dict) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
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


async def fetch_image(pid: [int, str]) -> Result:
    # 获取illust
    payload = {'key': API_KEY, 'pid': pid, 'mode': 'regular'}
    _res = await fetch_json(url=DOWNLOAD_API_URL, paras=payload)
    if _res.success() and not _res.result.get('error'):
        illust_data = _res.result.get('body')
        title = illust_data.get('title')
        author = illust_data.get('uname')
        url = illust_data.get('url')
        description = illust_data.get('description')
        tags = ''
        for tag in illust_data.get('tags'):
            tags += f'#{tag}  '
        if not description:
            msg = f'「{title}」/「{author}」\n{tags}\n{url}'
        else:
            msg = f'「{title}」/「{author}」\n{tags}\n{url}\n----------------\n{description[:28]}......'
        pic_b64 = illust_data.get('pic_b64')
        result = Result(error=False, info='Success', result={'msg': msg, 'b64': pic_b64})
    else:
        result = Result(error=True, info=f'网络超时或 {pid} 不存在', result={})
    return result
