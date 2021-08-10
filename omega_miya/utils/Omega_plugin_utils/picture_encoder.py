import os
import base64
import aiofiles
import pathlib
from nonebot import get_driver, logger
from omega_miya.utils.Omega_Base import Result
from omega_miya.utils.Omega_plugin_utils import HttpFetcher


driver = get_driver()
TMP_PATH = driver.config.tmp_path_


class PicEncoder(object):
    @classmethod
    async def file_to_b64(cls, file_path: str) -> Result.TextResult:
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return Result.TextResult(error=True, info='File not exists', result='')

        try:
            async with aiofiles.open(abs_path, 'rb') as af:
                b64 = base64.b64encode(await af.read())
            b64 = str(b64, encoding='utf-8')
            b64 = 'base64://' + b64
            return Result.TextResult(error=False, info='Success', result=b64)
        except Exception as e:
            logger.opt(colors=True).warning(f'<Y><lw>PicEncoder</lw></Y> file_to_b64 failed, <y>Error</y>: {repr(e)}')
            return Result.TextResult(error=True, info=repr(e), result='')

    @classmethod
    async def bytes_to_file(cls, image: bytes, *, folder_flag: str = 'PicEncoder') -> Result.TextResult:
        # 检查保存文件路径
        folder_path = os.path.abspath(os.path.join(TMP_PATH, folder_flag))
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        file_path = os.path.abspath(os.path.join(folder_path, str(hash(image))))
        try:
            async with aiofiles.open(file_path, 'wb') as af:
                await af.write(image)
            file_url = pathlib.Path(file_path).as_uri()
            return Result.TextResult(error=False, info='Success', result=file_url)
        except Exception as e:
            logger.opt(colors=True).warning(f'<Y><lw>PicEncoder</lw></Y> bytes_to_file failed, <y>Error</y>: {repr(e)}')
            return Result.TextResult(error=True, info=repr(e), result='')

    @classmethod
    def bytes_to_b64(cls, image: bytes) -> Result.TextResult:
        try:
            b64 = str(base64.b64encode(image), encoding='utf-8')
            b64 = 'base64://' + b64
            return Result.TextResult(error=False, info='Success', result=b64)
        except Exception as e:
            logger.opt(colors=True).warning(f'<Y><lw>PicEncoder</lw></Y> bytes_to_b64 failed, <y>Error</y>: {repr(e)}')
            return Result.TextResult(error=True, info=repr(e), result='')

    def __init__(
            self,
            pic_url: str,
            *,
            headers: dict = None,
            params: dict = None
    ):
        self.__pic_url = pic_url
        self.__headers = headers
        self.__params = params

    async def get_base64(self) -> Result.TextResult:
        fetcher = HttpFetcher(timeout=30, attempt_limit=2, flag='PicEncoder_get_base64', headers=self.__headers)
        bytes_result = await fetcher.get_bytes(url=self.__pic_url)
        if bytes_result.error:
            return Result.TextResult(error=True, info='Image download failed', result='')

        encode_result = self.bytes_to_b64(image=bytes_result.result)
        return encode_result

    async def get_file(self, *, folder_flag: str = 'PicEncoder') -> Result.TextResult:
        fetcher = HttpFetcher(timeout=30, attempt_limit=2, flag='PicEncoder_get_base64', headers=self.__headers)
        bytes_result = await fetcher.get_bytes(url=self.__pic_url)
        if bytes_result.error:
            return Result.TextResult(error=True, info='Image download failed', result='')

        encode_result = await self.bytes_to_file(image=bytes_result.result, folder_flag=folder_flag)
        return encode_result


__all__ = [
    'PicEncoder'
]
