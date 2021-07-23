"""
@Author         : Ailitonia
@Date           : 2021/05/30 16:48
@FileName       : data_source.py
@Project        : nonebot2_miya 
@Description    : Http Cat Utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import pathlib
from nonebot import get_driver
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result

global_config = get_driver().config
TMP_PATH = global_config.tmp_path_

API_URL = 'https://http.cat/'


async def get_http_cat(http_code: int) -> Result.TextResult:
    file_name = f'{http_code}.jpg'
    folder_path = os.path.abspath(os.path.join(TMP_PATH, 'http_cat'))
    file_path = os.path.abspath(os.path.join(folder_path, file_name))
    if os.path.exists(file_path):
        file_url = pathlib.Path(file_path).as_uri()
        return Result.TextResult(error=False, info='Success, file exists', result=file_url)

    url = f'{API_URL}{http_code}.jpg'
    fetcher = HttpFetcher(timeout=10, flag='http_cat')
    result = await fetcher.download_file(url=url, path=folder_path, file_name=file_name)

    if result.success():
        file_url = pathlib.Path(result.result).as_uri()
        return Result.TextResult(error=False, info='Success', result=file_url)
    else:
        return Result.TextResult(error=True, info=result.info, result='')
