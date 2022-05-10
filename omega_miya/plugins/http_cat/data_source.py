"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:48
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : Http Cat Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.web_resource import HttpFetcher
from omega_miya.local_resource import TmpResource
from omega_miya.utils.process_utils import run_async_catching_exception


_API_URL = 'https://http.cat/'
"HttpCat Api"
_TMP_FOLDER: TmpResource = TmpResource('http_cat')


@run_async_catching_exception
async def get_http_cat(http_code: int | str) -> TmpResource:
    file = _TMP_FOLDER(f'{http_code}.jpg')
    if file.path.exists() and file.path.is_file():
        return file

    download_result = await HttpFetcher().download_file(url=f'{_API_URL}{http_code}.jpg', file=file)
    if download_result.status == 404:
        pass
    elif download_result.status != 200:
        raise RuntimeError(f'download httpcat {http_code} failed')
    return file


__all__ = [
    'get_http_cat'
]
