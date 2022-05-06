"""
@Author         : Ailitonia
@Date           : 2022/04/05 3:27
@FileName       : __init__.py
@Project        : nonebot2_miya 
@Description    : 本地资源文件模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import os
import sys
import pathlib
import aiofiles
from copy import deepcopy
from typing import Generator, IO, TypeVar, ParamSpec, Callable, Optional, Any
from functools import wraps
from contextlib import contextmanager, asynccontextmanager

from omega_miya.exception import LocalSourceException


class ResourceNotFolderError(LocalSourceException):
    """LocalResource 实例不是文件夹"""


class ResourceNotFileError(LocalSourceException):
    """LocalResource 实例不是文件"""


P = ParamSpec("P")
R = TypeVar("R")


# 初始化静态资源文件及临时文件储存路径
_local_resource_folder = pathlib.Path(os.path.abspath(os.path.dirname(__file__)))
_local_tmp_resource_folder = pathlib.Path(os.path.abspath(sys.path[0])).joinpath('tmp')
if not _local_tmp_resource_folder.exists():
    _local_tmp_resource_folder.mkdir()


class LocalResource(object):
    """静态资源文件"""
    _local_resource_root: pathlib.Path = _local_resource_folder

    def __init__(self, *args: str):
        self.path = self._local_resource_root
        if args:
            self.path = self.path.joinpath(*[str(x) for x in args])

    def __repr__(self) -> str:
        return f'<LocalResource(path={self.path})>'

    def __call__(self, *args) -> "LocalResource":
        new_obj = deepcopy(self)
        new_obj.path = self.path.joinpath(*[str(x) for x in args])
        return new_obj

    @staticmethod
    def check_directory(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要实例 path 为文件夹时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "LocalResource" = args[0]
            if self.path.exists() and self.path.is_dir():
                return func(*args, **kwargs)
            else:
                raise ResourceNotFolderError(f'"{self.path}" is not a directory, or directory {self.path} not exists')
        return _wrapper

    @staticmethod
    def check_file(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要实例 path 为文件时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "LocalResource" = args[0]
            if self.path.exists() and self.path.is_file():
                return func(*args, **kwargs)
            elif not self.path.exists():
                if not self.path.parent.exists():
                    pathlib.Path.mkdir(self.path.parent, parents=True)
                return func(*args, **kwargs)
            else:
                raise ResourceNotFileError(f'"{self.path}" is not a file, or file {self.path} not exists')
        return _wrapper

    @property
    def resolve_path(self) -> str:
        return str(self.path.resolve())

    @property
    @check_file
    def file_uri(self) -> str:
        return self.path.as_uri()

    @contextmanager
    @check_file
    def open(self, mode, encoding: Optional[str] = None, **kwargs) -> Generator[IO, Any, None]:
        """返回文件 handle"""
        with self.path.open(mode=mode, encoding=encoding, **kwargs) as _fh:
            yield _fh

    @asynccontextmanager
    @check_file
    async def async_open(self, mode, encoding: Optional[str] = None, **kwargs):
        """返回文件 async handle"""
        async with aiofiles.open(file=self.path, mode=mode, encoding=encoding, **kwargs) as _afh:
            yield _afh

    @check_directory
    def list_all_files(self) -> list["LocalResource"]:
        """遍历文件夹内所有文件并返回文件列表"""
        file_list = []
        for dir_path, dir_names, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file_list.append(LocalResource(dir_path, file_name))
        return file_list

    @check_directory
    def sync_handle_all_files(self, mode, encoding: Optional[str] = None, **kwargs) -> Generator[IO, Any, None]:
        """遍历文件夹内所有文件"""
        for dir_path, dir_names, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file = self.path.joinpath(dir_path, file_name)
                    with file.open(mode=mode, encoding=encoding, **kwargs) as _fh:
                        yield _fh

    @check_directory
    async def async_handle_all_files(self, mode, encoding: Optional[str] = None, **kwargs):
        """异步遍历文件夹内所有文件"""
        for dir_path, dir_names, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file = self.path.joinpath(dir_path, file_name)
                    async with aiofiles.open(file=file, mode=mode, encoding=encoding, **kwargs) as _afh:
                        yield _afh

    @check_file
    async def async_read_text_line(self, encoding: Optional[str] = 'utf-8', **kwargs):
        """返回按行读取文件内容的生成器"""
        async with self.async_open(mode='r', encoding=encoding, **kwargs) as _af:
            async for _line in _af:
                yield _line


class TmpResource(LocalResource):
    """临时文件"""
    _local_resource_root: pathlib.Path = _local_tmp_resource_folder


__all__ = [
    'LocalResource',
    'TmpResource',
    'ResourceNotFolderError',
    'ResourceNotFileError'
]
