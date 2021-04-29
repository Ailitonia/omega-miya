import os
import zipfile
import asyncio
from typing import List
from nonebot.log import logger
from omega_miya.utils.Omega_Base import Result


def __create_zip_file(files: List[str], file_path: str, file_name: str) -> Result.TextResult:
    # 检查文件路径
    folder_path = os.path.abspath(file_path)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    zip_file_path = os.path.abspath(os.path.join(folder_path, f'{file_name}.zip'))
    with zipfile.ZipFile(zip_file_path, mode='w', compression=zipfile.ZIP_STORED) as zipf:
        for file in files:
            file_path = os.path.abspath(file)
            arcname = os.path.basename(file_path)
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=arcname)
            else:
                logger.warning(f'create_zip_file: file not exists: {file}, ignore')

    return Result.TextResult(error=False, info=f'{file_name}.zip', result=zip_file_path)


async def create_zip_file(files: List[str], file_path: str, file_name: str) -> Result.TextResult:
    def __handle():
        return __create_zip_file(files, file_path, file_name)

    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(None, __handle)
    except Exception as e:
        result = Result.TextResult(error=True, info=repr(e), result='')

    return result


__all__ = [
    'create_zip_file'
]
