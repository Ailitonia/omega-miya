"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:25
@FileName       : zip_utils.py
@Project        : nonebot2_miya
@Description    : 压缩文件创建工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pathlib
import zipfile
import py7zr

from omega_miya.local_resource import LocalResource, TmpResource
from omega_miya.utils.process_utils import run_sync

from .config import zip_utils_config, zip_utils_resource_config


class ZipUtils(object):
    def __init__(self, file_name: str):
        self._file: TmpResource = zip_utils_resource_config.default_storage_folder(file_name)

    def _create_zip(
            self,
            files: list[LocalResource],
            *,
            compression: int = zipfile.ZIP_STORED) -> TmpResource:
        """创建 zip 压缩文件

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        if self._file.path.suffix != '.zip':
            raise ValueError('File suffix must be ".zip"')
        if not self._file.path.parent.exists():
            pathlib.Path.mkdir(self._file.path.parent, parents=True)

        with zipfile.ZipFile(self._file.path.resolve(), mode='w', compression=compression) as zipf:
            for file in files:
                if file.path.exists() and file.path.is_file():
                    zipf.write(file.path.resolve(), arcname=file.path.name)
        return self._file

    async def create_zip(
            self,
            files: list[LocalResource],
            *,
            compression: int = zipfile.ZIP_STORED) -> TmpResource:
        """创建 zip 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        return await run_sync(self._create_zip)(files=files, compression=compression)

    def _create_7z(
            self,
            files: list[LocalResource],
            *,
            password: str | None = None) -> TmpResource:
        """创建 7z 压缩文件

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        if self._file.path.suffix != '.7z':
            raise ValueError('File suffix must be ".7z"')
        if not self._file.path.parent.exists():
            pathlib.Path.mkdir(self._file.path.parent, parents=True)

        with py7zr.SevenZipFile(self._file.path.resolve(), mode='w', password=password) as zf:
            if password:
                zf.set_encrypted_header(True)
            for file in files:
                if file.path.exists() and file.path.is_file():
                    zf.write(file.path.resolve(), arcname=file.path.name)
        return self._file

    async def create_7z(
            self,
            files: list[LocalResource],
            *,
            password: str | None = None) -> TmpResource:
        """创建 7z 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        return await run_sync(self._create_7z)(files=files, password=password)


__all__ = [
    'ZipUtils'
]
