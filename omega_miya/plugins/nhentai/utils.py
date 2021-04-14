import nonebot
import os
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result


global_config = nonebot.get_driver().config
API_KEY = global_config.api_key
SEARCH_API_URL = f'{global_config.api_url}/api/nhentai/search/'
DOWNLOAD_API_URL = f'{global_config.api_url}/api/nhentai/download/'
GET_API_URL = f'{global_config.api_url}/api/nhentai/get/'

ENABLE_PROXY = global_config.enable_proxy
PROXY_ADDRESS = global_config.proxy_address
PROXY_PORT = global_config.proxy_port
# 检查proxy
if ENABLE_PROXY:
    PROXY = f'http://{PROXY_ADDRESS}:{PROXY_PORT}'
else:
    PROXY = None

HEADERS = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                         'Chrome/89.0.4389.114 Safari/537.36'}


async def nh_search(tag: str) -> Result:
    payload = {'key': API_KEY, 'tag': tag}
    fetcher = HttpFetcher(timeout=90, flag='nhentai_search', headers=HEADERS, proxy=PROXY)
    _res = await fetcher.get_json(url=SEARCH_API_URL, params=payload)
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
    fetcher = HttpFetcher(timeout=180, flag='nhentai_download', headers=HEADERS, proxy=PROXY)
    server_dl = await fetcher.get_json(url=DOWNLOAD_API_URL, params=dl_payload)
    if not server_dl.success():
        return server_dl

    dl_result = dict(server_dl.result.get('body'))
    password = dl_result.get('password')

    # 本地已经下载过了就不再下载
    if os.path.exists(file):
        return Result(error=False, info='File exist', result={'file': file, 'password': password})

    # 尝试从服务器下载资源
    file_download = await fetcher.get_bytes(url=GET_API_URL, params=dl_payload)
    if file_download.success():
        try:
            with open(file, 'wb+') as f:
                f.write(file_download.result)
            return Result(error=False, info='Success', result={'file': file, 'password': password})
        except Exception as e:
            return Result(error=True, info=f'Save file failed, {repr(e)}', result={})
    else:
        return Result(error=True, info=f'Download failed, {file_download.info}', result={})
