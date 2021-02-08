import aiohttp
import nonebot
import os
from omega_miya.utils.Omega_Base import Result


global_config = nonebot.get_driver().config
API_KEY = global_config.api_key
SEARCH_API_URL = f'{global_config.api_url}/api/nhentai/search/'
DOWNLOAD_API_URL = f'{global_config.api_url}/api/nhentai/download/'
GET_API_URL = f'{global_config.api_url}/api/nhentai/get/'


async def fetch_json(url: str, paras: dict) -> Result:
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=90)
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


async def nh_search(tag: str) -> Result:
    payload = {'key': API_KEY, 'tag': tag}
    _res = await fetch_json(url=SEARCH_API_URL, paras=payload)
    if _res.success() and not _res.result.get('error'):
        result = _res
    else:
        result = Result(error=True, info=f'网络超时或其他错误: {_res.info}', result={})
    return result


# 下载文件
async def nh_download(_id) -> Result:
    plugin_path = os.path.dirname(__file__)
    sub_dir = os.path.join(plugin_path, 'nhentai_gallery')
    if not os.path.exists(sub_dir):
        os.makedirs(sub_dir)

    file = os.path.join(sub_dir, f'{_id}.7z')

    # 确认服务端远端下载并获取密码
    dl_payload = {'key': API_KEY, 'id': _id}
    server_dl = await fetch_json(url=DOWNLOAD_API_URL, paras=dl_payload)
    if not server_dl.success():
        return server_dl

    dl_result = dict(server_dl.result.get('body'))
    password = dl_result.get('password')

    # 本地已经下载过了就不再下载
    if os.path.exists(file):
        return Result(error=False, info='File exist', result={'file': file, 'password': password})

    # 尝试从服务器下载资源
    error_info = ''
    timeout_count = 0
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=180)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'}
                async with session.get(url=GET_API_URL, headers=headers, params=dl_payload, timeout=timeout) as resp:
                    nh_file = await resp.read()
                    with open(file, 'wb+') as f:
                        f.write(nh_file)
                        return Result(error=False, info='Success', result={'file': file, 'password': password})
        except Exception as _e:
            error_info += f'{__name__}: {repr(_e)} Occurred in getting trying {timeout_count + 1} with id: {_id}'
        finally:
            timeout_count += 1
    else:
        error_info += f'{__name__}: Failed too many times in getting with id: {_id}'
        return Result(error=True, info=f'Download failed, error info: {error_info}', result={})
