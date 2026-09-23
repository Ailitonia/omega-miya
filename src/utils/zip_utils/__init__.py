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
from collections.abc import Callable, Sequence
from uuid import uuid4

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
    ) -> list[BaseResource]:
        """压缩前校验, 返回排除了目标文件自身的有效待压缩文件列表

        纯校验, 不修改任何既有文件, 全部校验通过后才允许进入写入阶段

        :param files: 被压缩的文件列表
        :param expected_suffix: 目标文件后缀
        :return: 排除了目标文件自身的有效待压缩文件列表
        """
        if self.file.suffix.lower() != expected_suffix:
            raise ValueError(f'File suffix must be "{expected_suffix}"')

        # 排除如存在的压缩文档自身, 避免写入时无限递归
        _effective = [file for file in files if file.resolve_path != self.file.resolve_path]
        if not _effective:
            raise ValueError('No files to archive')

        _missing = [file.resolve_path for file in _effective if not file.is_file]
        if _missing:
            raise ValueError(f'Files not found or not a file: {_missing}')

        _names = [file.name for file in _effective]
        _duplicates = sorted({name for name in _names if _names.count(name) > 1})
        if _duplicates:
            raise ValueError(f'Duplicate file names in archive: {_duplicates}')

        if self.file.is_file and not self.overwrite:
            raise RuntimeError(f'File {self.file} already exists')

        self.file.ensure_parent_path()
        return _effective

    def _atomic_write(
            self,
            write: Callable[[str], None],
    ) -> None:
        """在同目录临时文件上执行写入, 成功后原子替换目标文件, 任何异常都会清理临时文件

        既有目标文件在原子替换前全程不被修改, 写入失败时目标文件保持原样

        :param write: 接受临时文件路径并执行实际压缩写入的回调
        """
        _tmp_file = self.file.with_suffix(f'.{uuid4().hex}.tmp')
        try:
            write(_tmp_file.resolve_path)
        except Exception:
            _tmp_file.remove(missing_ok=True)
            raise
        try:
            _tmp_file.replace(self.file.path)
        except OSError as e:
            _tmp_file.remove(missing_ok=True)
            raise RuntimeError(f'写入压缩文件失败: {e}') from e

    @run_sync
    def _create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> None:
        """创建 zip 压缩文件

        先写入临时文件再原子替换目标文件, 写入失败时既有目标文件不受影响

        :param files: 被压缩的文件列表
        :param compression: 压缩方法常量, zipfile.ZIP_STORED/ZIP_DEFLATED/ZIP_LZMA/ZIP_BZIP2 之一, 缺省用配置默认值
        """
        compression = zip_utils_config.zip_utils_default_zip_compression if compression is None else compression

        _allowed_compression = (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2)
        if compression not in _allowed_compression:
            raise ValueError(f'compression must be one of {_allowed_compression}, got {compression!r}')

        _files = self._prepare_target(files, expected_suffix='.zip')

        def _write(path: str) -> None:
            with zipfile.ZipFile(path, mode='w', compression=compression) as zipf:
                for file in _files:
                    zipf.write(file.resolve_path, arcname=file.name)

        self._atomic_write(_write)

    async def create_zip(
            self,
            files: Sequence[BaseResource],
            *,
            compression: int | None = None
    ) -> TemporaryResource:
        """创建 zip 压缩文件, 异步方法

        先写入临时文件再原子替换目标文件, 写入失败时既有目标文件不受影响

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

        先写入临时文件再原子替换目标文件, 写入失败时既有目标文件不受影响

        :param files: 被压缩的文件列表
        :param password: 文件密码, 空字符串视为无密码
        """
        password = password or None
        _files = self._prepare_target(files, expected_suffix='.7z')

        def _write(path: str) -> None:
            with py7zr.SevenZipFile(path, mode='w', password=password) as zf:
                if password:
                    zf.set_encrypted_header(True)
                for file in _files:
                    zf.write(file.resolve_path, arcname=file.name)

        self._atomic_write(_write)

    async def create_7z(
            self,
            files: Sequence[BaseResource],
            *,
            password: str | None = None
    ) -> TemporaryResource:
        """创建 7z 压缩文件, 异步方法

        先写入临时文件再原子替换目标文件, 写入失败时既有目标文件不受影响

        :param files: 被压缩的文件列表
        :param password: 文件密码, 空字符串视为无密码
        """
        await self._create_7z(files=files, password=password)
        return self.file


__all__ = [
    'ZipUtils'
]
