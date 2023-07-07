"""
@Author         : Ailitonia
@Date           : 2022/04/05 3:27
@FileName       : resource.py
@Project        : nonebot2_miya 
@Description    : 本地资源文件模块
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import abc
import os
import sys
import pathlib
import aiofiles
from copy import deepcopy
from typing import Generator, IO, TypeVar, ParamSpec, Callable, Optional, Any
from functools import wraps
from contextlib import contextmanager, asynccontextmanager

from src.exception import LocalSourceException


class ResourceNotFolderError(LocalSourceException):
    """LocalResource 实例不是文件夹"""


class ResourceNotFileError(LocalSourceException):
    """LocalResource 实例不是文件"""


P = ParamSpec("P")
R = TypeVar("R")


_static_resource_folder = pathlib.Path(os.path.abspath(sys.path[0])).joinpath('static')
"""静态资源文件路径"""
_temporary_resource_folder = pathlib.Path(os.path.abspath(sys.path[0])).joinpath('.tmp')
"""临时文件文件路径"""
if not _temporary_resource_folder.exists():  # 初始化临时文件路径所在文件夹
    _temporary_resource_folder.mkdir()


class BaseResource(abc.ABC):
    """资源文件基类"""

    @abc.abstractmethod
    def __init__(self, *args: str):
        self.path: pathlib.Path = ...
        if args:
            self.path = self.path.joinpath(*[str(x) for x in args])

    def __repr__(self) -> str:
        return f'<{self.__class__.__name__}(path={self.resolve_path!r})>'

    def __call__(self, *args) -> "BaseResource":
        new_obj = deepcopy(self)
        new_obj.path = self.path.joinpath(*[str(x) for x in args])
        return new_obj

    @property
    def is_exist(self) -> bool:
        return self.path.exists()

    @property
    def is_file(self) -> bool:
        return self.is_exist and self.path.is_file()

    @property
    def is_dir(self) -> bool:
        return self.is_exist and self.path.is_dir()

    @staticmethod
    def check_directory(func: Callable[P, R]) -> Callable[P, R]:
        """装饰一个方法, 需要实例 path 为文件夹时才能运行"""
        @wraps(func)
        def _wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            self: "BaseResource" = args[0]
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
            self: "BaseResource" = args[0]
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
        return self.path.resolve().as_uri()

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
    def list_all_files(self) -> list["BaseResource"]:
        """遍历文件夹内所有文件并返回文件列表"""
        file_list = []
        for dir_path, dir_names, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file_list.append(self.__class__(dir_path, file_name))
        return file_list

    @check_file
    async def async_read_text_line(self, encoding: Optional[str] = 'utf-8', **kwargs):
        """返回按行读取文件内容的生成器"""
        async with self.async_open(mode='r', encoding=encoding, **kwargs) as _af:
            async for _line in _af:
                yield _line


class StaticResource(BaseResource):
    """静态资源文件"""
    def __init__(self, *args: str):
        self.path: pathlib.Path = deepcopy(_static_resource_folder)
        if args:
            self.path = self.path.joinpath(*[str(x) for x in args])


class TemporaryResource(BaseResource):
    """临时资源文件"""
    def __init__(self, *args: str):
        self.path: pathlib.Path = deepcopy(_temporary_resource_folder)
        if args:
            self.path = self.path.joinpath(*[str(x) for x in args])


__all__ = [
    'BaseResource',
    'StaticResource',
    'TemporaryResource',
    'ResourceNotFolderError',
    'ResourceNotFileError'
]
