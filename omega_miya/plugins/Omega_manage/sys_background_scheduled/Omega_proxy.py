import aiohttp
import nonebot
from nonebot import logger
from omega_miya.utils.Omega_Base import DBStatus, Result

global_config = nonebot.get_driver().config
ENABLE_PROXY = global_config.enable_proxy
PROXY_ADDRESS = global_config.proxy_address
PROXY_PORT = global_config.proxy_port


async def test_proxy(proxy_address: str, proxy_port: int) -> Result:
    test_url = 'https://api.bilibili.com/x/web-interface/nav'
    proxy = f'http://{proxy_address}:{proxy_port}'
    timeout_count = 0
    error_info = ''
    while timeout_count < 3:
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                headers = {'accept': 'application/json; charset=utf-8',
                           'accept-encoding': 'gzip, deflate',
                           'accept-language': 'zh-CN,zh;q=0.9',
                           'origin': 'https://www.bilibili.com',
                           'referer': 'https://www.bilibili.com/',
                           'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                                         'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36'}
                async with session.get(url=test_url, headers=headers, proxy=proxy, timeout=timeout) as resp:
                    _json = await resp.json()
                    _status = resp.status
                if _status == 200 and _json:
                    result = Result(error=False, info='Success', result=_status)
                else:
                    result = Result(error=True, info=f'Status: {_status}', result=_status)
            return result
        except Exception as e:
            error_info += f'{repr(e)} Occurred in test_proxy trying {timeout_count + 1}\n'
        finally:
            timeout_count += 1
    else:
        error_info += f'Failed too many times in test_proxy'
        result = Result(error=True, info=error_info, result=-1)
        return result


# 检查代理可用性的状态的任务
async def check_proxy():
    if not ENABLE_PROXY:
        return

    result = await test_proxy(proxy_address=PROXY_ADDRESS, proxy_port=PROXY_PORT)
    if result.success():
        db_res = DBStatus(name='PROXY_AVAILABLE').set_status(status=1, info='代理可用')
        logger.opt(colors=True).info(f'代理检查: <g>成功, status: {result.result}!</g>, DB info: {db_res.info}')
    else:
        db_res = DBStatus(name='PROXY_AVAILABLE').set_status(status=0, info='代理不可用')
        logger.opt(colors=True).warning(f'代理检查: <y>失败, status: {result.result}, '
                                        f'info: {result.info}!</y>, DB info: {db_res.info}')
__all__ = [
    'ENABLE_PROXY',
    'check_proxy'
]
