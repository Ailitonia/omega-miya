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

from nonebot.utils import run_sync

from src.resource import BaseResource, TemporaryResource

from .config import zip_utils_config, zip_utils_resource_config


class ZipUtils(object):
    def __init__(self, file_name: str):
        self.file: TemporaryResource = zip_utils_resource_config.default_storage_folder(file_name)

    def _create_zip(
            self,
            files: list[BaseResource],
            *,
            compression: int | None = None) -> TemporaryResource:
        """创建 zip 压缩文件

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        compression = zip_utils_config.default_zip_compression if compression is None else compression

        if self.file.path.suffix != '.zip':
            raise ValueError('File suffix must be ".zip"')

        if not self.file.path.parent.exists():
            pathlib.Path.mkdir(self.file.path.parent, parents=True)

        with zipfile.ZipFile(self.file.path.resolve(), mode='w', compression=compression) as zipf:
            for file in files:
                if file.path.exists() and file.path.is_file():
                    zipf.write(file.path.resolve(), arcname=file.path.name)
        return self.file

    async def create_zip(
            self,
            files: list[BaseResource],
            *,
            compression: int | None = None) -> TemporaryResource:
        """创建 zip 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        return await run_sync(self._create_zip)(files=files, compression=compression)

    def _create_7z(
            self,
            files: list[BaseResource],
            *,
            password: str | None = None) -> TemporaryResource:
        """创建 7z 压缩文件

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        if self.file.path.suffix != '.7z':
            raise ValueError('File suffix must be ".7z"')

        if not self.file.path.parent.exists():
            pathlib.Path.mkdir(self.file.path.parent, parents=True)

        with py7zr.SevenZipFile(self.file.path.resolve(), mode='w', password=password) as zf:
            if password:
                zf.set_encrypted_header(True)
            for file in files:
                if file.path.exists() and file.path.is_file():
                    zf.write(file.path.resolve(), arcname=file.path.name)
        return self.file

    async def create_7z(
            self,
            files: list[BaseResource],
            *,
            password: str | None = None) -> TemporaryResource:
        """创建 7z 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        return await run_sync(self._create_7z)(files=files, password=password)


__all__ = [
    'ZipUtils'
]
