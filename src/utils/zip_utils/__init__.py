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
        if folder is not None:
            folder.raise_not_dir()
            storage_folder: TemporaryResource = folder
        else:
            storage_folder = zip_utils_config.default_output_folder

        self.file: TemporaryResource = storage_folder(file_name)
        self.overwrite = overwrite

    def _prepare_target(
            self,
            files: Sequence[BaseResource],
            *,
            expected_suffix: str,
    ) -> None:
        """压缩前校验并准备目标文件: 全部校验通过后才允许替换既有目标文件

        :param files: 被压缩的文件列表
        :param expected_suffix: 目标文件后缀
        """
        if self.file.suffix != expected_suffix:
            raise ValueError(f'File suffix must be "{expected_suffix}"')

        _missing = [
            file.resolve_path
            for file in files
            if file.resolve_path != self.file.resolve_path and not file.is_file
        ]
        if _missing:
            raise ValueError(f'Files not found or not a file: {_missing}')

        if self.file.is_file:
            if not self.overwrite:
                raise RuntimeError(f'File {self.file} already exists')
            self.file.remove()

        self.file.ensure_parent_path()

    @run_sync
    def _create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> None:
        """创建 zip 压缩文件

        :param files: 被压缩的文件列表
        :param compression: 压缩方法常量, zipfile.ZIP_STORED/ZIP_DEFLATED/ZIP_LZMA/ZIP_BZIP2 之一, 缺省用配置默认值
        """
        compression = zip_utils_config.zip_utils_default_zip_compression if compression is None else compression

        _allowed_compression = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2)
        if compression not in _allowed_compression:
            raise ValueError(f'compression must be one of {_allowed_compression}, got {compression!r}')

        self._prepare_target(files, expected_suffix='.zip')

        with zipfile.ZipFile(self.file.resolve_path, mode='w', compression=compression) as zipf:
            for file in files:
                if file.resolve_path == self.file.resolve_path:
                    # 跳过如存在的压缩文档自身避免无限递归
                    continue
                zipf.write(file.resolve_path, arcname=file.name)

    async def create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> TemporaryResource:
        """创建 zip 压缩文件, 异步方法

        :param files: 被压缩的文件列表
        :param compression: 压缩方法常量, zipfile.ZIP_STORED/ZIP_DEFLATED/ZIP_LZMA/ZIP_BZIP2 之一, 缺省用配置默认值
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
        self._prepare_target(files, expected_suffix='.7z')

        with py7zr.SevenZipFile(self.file.resolve_path, mode='w', password=password) as zf:
            if password:
                zf.set_encrypted_header(True)
            for file in files:
                if file.resolve_path == self.file.resolve_path:
                    # 跳过如存在的压缩文档自身避免无限递归
                    continue
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
