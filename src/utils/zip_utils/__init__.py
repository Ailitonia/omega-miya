"""
@Author         : Ailitonia
@Date           : 2022/04/10 21:25
@FileName       : zip_utils.py
@Project        : nonebot2_miya
@Description    : 压缩文件创建工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import zipfile
from collections.abc import Sequence

import py7zr
from nonebot.utils import run_sync

from src.resource import BaseResource, TemporaryResource
from .config import zip_utils_config


class ZipUtils:
    def __init__(
            self,
            file_name: str,
            *,
            folder: TemporaryResource | None = None,
            overwrite: bool = True,
    ) -> None:
        if folder is not None and folder.is_dir:
            storage_folder: TemporaryResource = folder
        else:
            storage_folder: TemporaryResource = zip_utils_config.default_output_folder

        self.file: TemporaryResource = storage_folder(file_name)
        self.overwrite = overwrite

    @run_sync
    def _create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> None:
        """创建 zip 压缩文件

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        if self.file.is_file and not self.overwrite:
            raise RuntimeError(f'File {self.file} already exists')
        elif self.file.is_file and self.overwrite:
            self.file.remove()

        compression = zip_utils_config.zip_utils_default_zip_compression if compression is None else compression

        if self.file.suffix != '.zip':
            raise ValueError('File suffix must be ".zip"')

        self.file.ensure_parent_path()
        with zipfile.ZipFile(self.file.resolve_path, mode='w', compression=compression) as zipf:
            for file in files:
                if file.resolve_path == self.file.resolve_path:
                    # 跳过如存在的压缩文档自身避免无限递归
                    continue
                if file.is_file:
                    zipf.write(file.resolve_path, arcname=file.name)

    async def create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> TemporaryResource:
        """创建 zip 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param compression: 压缩级别参数
        """
        await self._create_zip(files=files, compression=compression)
        return self.file

    @run_sync
    def _create_7z(
            self,
            files: Sequence[BaseResource],
            *,
            password: str | None = None
    ) -> None:
        """创建 7z 压缩文件

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        if self.file.is_file and not self.overwrite:
            raise RuntimeError(f'File {self.file} already exists')
        elif self.file.is_file and self.overwrite:
            self.file.remove()

        if self.file.suffix != '.7z':
            raise ValueError('File suffix must be ".7z"')

        self.file.ensure_parent_path()
        with py7zr.SevenZipFile(self.file.resolve_path, mode='w', password=password) as zf:
            if password:
                zf.set_encrypted_header(True)
            for file in files:
                if file.resolve_path == self.file.resolve_path:
                    # 跳过如存在的压缩文档自身避免无限递归
                    continue
                if file.is_file:
                    zf.write(file.resolve_path, arcname=file.name)

    async def create_7z(
            self,
            files: Sequence[BaseResource],
            *,
            password: str | None = None
    ) -> TemporaryResource:
        """创建 7z 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param password: 文件密码
        """
        await self._create_7z(files=files, password=password)
        return self.file


__all__ = [
    'ZipUtils'
]
