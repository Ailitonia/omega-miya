import nonebot
from nonebot import logger
from omega_miya.utils.Omega_Base import DBStatus, Result
from omega_miya.utils.Omega_plugin_utils import HttpFetcher

global_config = nonebot.get_driver().config
ENABLE_PROXY = global_config.enable_proxy
PROXY_ADDRESS = global_config.proxy_address
PROXY_PORT = global_config.proxy_port


async def test_proxy(proxy_address: str, proxy_port: int) -> Result:
    test_url = 'https://api.bilibili.com/x/web-interface/nav'
    proxy = f'http://{proxy_address}:{proxy_port}'
    headers = {'accept': 'application/json; charset=utf-8',
               'accept-encoding': 'gzip, deflate',
               'accept-language': 'zh-CN,zh;q=0.9',
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

    fetcher = HttpFetcher(timeout=5, flag='Omega_proxy', headers=headers, proxy=proxy)
    fetcher_result = await fetcher.get_json(url=test_url)

    if fetcher_result.success() and fetcher_result.status == 200:
        result = Result(error=False, info='Success', result=fetcher_result.status)
    else:
        result = Result(error=True, info=f'Status: {fetcher_result.status}', result=fetcher_result.status)
    return result


# 检查代理可用性的状态的任务
async def check_proxy():
    if not ENABLE_PROXY:
        return

    result = await test_proxy(proxy_address=PROXY_ADDRESS, proxy_port=PROXY_PORT)
    if result.success():
        db_res = await DBStatus(name='PROXY_AVAILABLE').set_status(status=1, info='代理可用')
        logger.opt(colors=True).info(f'代理检查: <g>成功! status: {result.result}</g>, DB info: {db_res.info}')
    else:
        db_res = await DBStatus(name='PROXY_AVAILABLE').set_status(status=0, info='代理不可用')
        logger.opt(colors=True).error(f'代理检查: <r>失败! status: {result.result}, '
                                      f'info: {result.info}</r>, DB info: {db_res.info}')


__all__ = [
    'ENABLE_PROXY',
    'check_proxy'
]
