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
import pathlib
import sys
from contextlib import contextmanager, asynccontextmanager
from copy import deepcopy
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ContextManager,
    Generator,
    NoReturn,
    IO,
    Literal,
    Optional,
    Self,
    overload
)

import aiofiles

from src.exception import LocalSourceException

if TYPE_CHECKING:
    from aiofiles.threadpool.binary import AsyncFileIO
    from aiofiles.threadpool.text import AsyncTextIOWrapper
    from io import FileIO, TextIOWrapper


class ResourceNotFolderError(LocalSourceException):
    """LocalResource 实例不是文件夹"""


class ResourceNotFileError(LocalSourceException):
    """LocalResource 实例不是文件"""


_static_resource_folder = pathlib.Path(os.path.abspath(sys.path[0])).joinpath('static')
"""静态资源文件路径"""
_temporary_resource_folder = pathlib.Path(os.path.abspath(sys.path[0])).joinpath('.tmp')
"""临时文件文件路径"""
if not _temporary_resource_folder.exists():  # 初始化临时文件路径所在文件夹
    _temporary_resource_folder.mkdir()


class BaseResource(abc.ABC):
    """资源文件基类"""

    __slots__ = ('path',)
    path: pathlib.Path

    @abc.abstractmethod
    def __init__(self, *args: str | pathlib.PurePath):
        raise NotImplementedError

    def __call__(self, *args: str | pathlib.PurePath) -> Self:
        new_obj = deepcopy(self)
        new_obj.path = self.path.joinpath(*args)
        return new_obj

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.resolve_path!r})'

    def __str__(self) -> str:
        return self.resolve_path

    @property
    def is_exist(self) -> bool:
        """路径目标文件/文件夹是否存在"""
        return self.path.exists()

    @property
    def is_file(self) -> bool:
        """路径目标是否为文件且存在"""
        return self.is_exist and self.path.is_file()

    @property
    def is_dir(self) -> bool:
        """路径目标是否为文件夹且存在"""
        return self.is_exist and self.path.is_dir()

    def raise_not_file(self) -> Optional[NoReturn]:
        """路径目标不是文件或不存在时抛出 ResourceNotFileError 异常"""
        if not self.is_file:
            raise ResourceNotFileError(f'"{self}" is not a file, or file "{self}" is not exists')

    def raise_not_dir(self) -> Optional[NoReturn]:
        """路径目标不是文件夹或不存在时抛出 ResourceNotFolderError 异常"""
        if not self.is_dir:
            raise ResourceNotFolderError(f'"{self}" is not a directory, or directory "{self}" is not exists')

    @staticmethod
    def check_directory(func):
        """装饰一个方法, 需要实例 path 为文件夹时才能运行"""
        @wraps(func)
        def _wrapper(self: Self, *args, **kwargs):
            if self.path.exists() and self.path.is_dir():
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFolderError(f'"{self}" is not a directory, or directory "{self}" is not exists')
        return _wrapper

    @staticmethod
    def check_file(func):
        """装饰一个方法, 需要实例 path 为文件时才能运行"""
        @wraps(func)
        def _wrapper(self: Self, *args, **kwargs):
            if self.path.exists() and self.path.is_file():
                return func(self, *args, **kwargs)
            elif not self.path.exists():
                if not self.path.parent.exists():
                    pathlib.Path.mkdir(self.path.parent, parents=True)
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFileError(f'"{self}" is not a file, or file "{self}" is not exists')
        return _wrapper

    @property
    def resolve_path(self) -> str:
        return str(self.path.resolve())

    @property
    @check_file
    def file_uri(self) -> str:
        return self.path.resolve().as_uri()

    @overload
    def open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: Optional[str] = None,
            **kwargs
    ) -> ContextManager["TextIOWrapper"]:
        ...

    @overload
    def open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: Optional[str] = None,
            **kwargs
    ) -> ContextManager["FileIO"]:
        ...

    @contextmanager
    @check_file
    def open(self, mode, encoding: Optional[str] = None, **kwargs) -> Generator[IO, Any, None]:
        """返回文件 handle"""
        with self.path.open(mode=mode, encoding=encoding, **kwargs) as _fh:
            yield _fh

    @overload
    def async_open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: Optional[str] = None,
            **kwargs
    ) -> AsyncContextManager["AsyncTextIOWrapper"]:
        ...

    @overload
    def async_open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: Optional[str] = None,
            **kwargs
    ) -> AsyncContextManager["AsyncFileIO"]:
        ...

    @asynccontextmanager
    @check_file
    async def async_open(self, mode, encoding: Optional[str] = None, **kwargs):
        """返回文件 async handle"""
        async with aiofiles.open(file=self.path, mode=mode, encoding=encoding, **kwargs) as _afh:
            yield _afh

    @check_directory
    def list_all_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表"""
        file_list = []
        for dir_path, _, file_names in os.walk(self.path):
            if file_names:
                for file_name in file_names:
                    file_list.append(self.__class__(dir_path, file_name))
        return file_list

    @check_directory
    def list_current_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表(不包含子目录)"""
        file_list = []
        for file_name in os.listdir(self.path):
            file = self.__class__(self.path, file_name)
            if file.is_file:
                file_list.append(file)
        return file_list


class StaticResource(BaseResource):
    """静态资源文件"""

    def __init__(self, *args: str | pathlib.PurePath):
        self.path: pathlib.Path = deepcopy(_static_resource_folder)
        if args:
            self.path = self.path.joinpath(*args)


class TemporaryResource(BaseResource):
    """临时资源文件"""

    def __init__(self, *args: str | pathlib.PurePath):
        self.path: pathlib.Path = deepcopy(_temporary_resource_folder)
        if args:
            self.path = self.path.joinpath(*args)


__all__ = [
    'BaseResource',
    'StaticResource',
    'TemporaryResource',
    'ResourceNotFolderError',
    'ResourceNotFileError',
]
