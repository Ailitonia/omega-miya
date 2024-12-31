"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:48
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : Http Cat Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from src.exception import WebSourceException
from src.resource import TemporaryResource
from src.utils import OmegaRequests

_TMP_FOLDER: TemporaryResource = TemporaryResource('http_cat')
"""缓存图片目录"""


async def get_http_cat(http_code: int | str) -> TemporaryResource:
    file = _TMP_FOLDER(f'{http_code}.jpg')
    if file.is_file:
        return file

    try:
        url = f'https://http.cat/{http_code}.jpg'
        await OmegaRequests().download(url=url, file=file)
    except WebSourceException:
        url = 'https://http.cat/404.jpg'
        await OmegaRequests().download(url=url, file=file)
    except Exception as e:
        raise RuntimeError(f'download httpcat {http_code} failed, {e!r}') from e

    return file


__all__ = [
    'get_http_cat',
]
