"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:48
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : Http Cat Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.utils.Omega_plugin_utils import HttpFetcher, PicEncoder
from omega_miya.utils.Omega_Base import Result

API_URL = 'https://http.cat/'


async def get_http_cat(http_code: int) -> Result.TextResult:
    url = f'{API_URL}{http_code}.jpg'

    fetcher = HttpFetcher(timeout=10, flag='http_cat')
    result = await fetcher.get_bytes(url=url)

    if result.error:
        return Result.TextResult(error=True, info=result.info, result='')

    encode_result = PicEncoder.bytes_to_b64(image=result.result)

    if encode_result.success():
        return Result.TextResult(error=False, info='Success', result=encode_result.result)
    else:
        return Result.TextResult(error=True, info=encode_result.info, result='')
