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
import sys
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ClassVar,
    Concatenate,
    ContextManager,
    Literal,
    NoReturn,
    Self,
    final,
    overload,
)

import aiofiles

from src.exception import LocalSourceException

if TYPE_CHECKING:
    from io import FileIO, TextIOWrapper

    from aiofiles.threadpool.binary import AsyncFileIO
    from aiofiles.threadpool.text import AsyncTextIOWrapper


@final
class ResourceNotFolderError(LocalSourceException):
    """LocalResource 实例不是文件夹"""

    @property
    def message(self) -> str:
        return f'{self.path.as_posix()!r} is not a directory, or directory {self.path.as_posix()!r} is not exists'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.path.as_posix()!r}, message={self.message})'


@final
class ResourceNotFileError(LocalSourceException):
    """LocalResource 实例不是文件"""

    @property
    def message(self) -> str:
        return f'{self.path.as_posix()!r} is not a file, or file {self.path.as_posix()!r} is not exists'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.path.as_posix()!r}, message={self.message})'


__ROOT_PATH: Path = Path(sys.path[0]).absolute()
"""项目根目录"""
_LOG_FOLDER: Path = __ROOT_PATH.joinpath('log')
"""日志文件路径"""
_STATIC_RESOURCE_FOLDER: Path = __ROOT_PATH.joinpath('static')
"""静态资源文件路径"""
_TEMPORARY_RESOURCE_FOLDER: Path = __ROOT_PATH.joinpath('.tmp')
"""运行时产生的的可随时清理的缓存/临时文件路径"""


# 初始化日志文件路径文件夹
if not _LOG_FOLDER.exists():
    _LOG_FOLDER.mkdir()

# 初始化临时文件路径文件夹
if not _TEMPORARY_RESOURCE_FOLDER.exists():
    _TEMPORARY_RESOURCE_FOLDER.mkdir()


class BaseResourceHostProtocol[RT: 'BaseResource'](abc.ABC):
    """文件托管协议基类"""

    def __init__(self, resource: RT) -> None:
        self._resource = resource

    @abc.abstractmethod
    async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> str:
        """获取文件托管路径, 返回文件 URL"""
        raise NotImplementedError


class BaseResource(abc.ABC):
    """资源文件基类"""

    _host_protocol: ClassVar[type[BaseResourceHostProtocol] | None] = None
    __slots__ = ('path',)
    path: Path

    @abc.abstractmethod
    def __init__(self, *args: str):
        raise NotImplementedError

    def __call__(self, *args: str) -> Self:
        new_obj = self.__class__(str(self.path))
        new_obj.path = self.path.joinpath(*args)
        return new_obj

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(path={self.resolve_path!r})'

    def __str__(self) -> str:
        return self.resolve_path

    @classmethod
    def init_from_path(cls, path: Path) -> Self:
        new_obj = cls()
        new_obj.path = path.absolute()
        return new_obj

    @classmethod
    def register_host_protocol(
            cls,
            protocol: type[BaseResourceHostProtocol],
    ) -> None:
        """注册文件托管协议"""
        if cls._host_protocol is not None:
            raise RuntimeError(f'host protocol already registered: {cls._host_protocol!r}')
        if not issubclass(protocol, BaseResourceHostProtocol):
            raise TypeError(f'protocol must be a subclass of BaseResourceHostProtocol, not {protocol!r}')
        cls._host_protocol = protocol

    @property
    def name(self) -> str:
        """一个表示最后路径组件的字符串, 排除了驱动器与根目录, 如果存在的话"""
        return self.path.name

    @property
    def suffix(self) -> str:
        """路径目标最终组件的文件扩展名(如果有)

        'my/library/setup.py' -> '.py'
        'my/library.tar.gz' -> .gz'
        'my/library' -> ''
        """
        return self.path.suffix

    @property
    def stem(self) -> str:
        """最后一个路径组件, 除去后缀

        'my/library.tar.gz' -> 'library.tar'
        'my/library.tar' -> 'library'
        'my/library' -> 'library'
        """
        return self.path.stem

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

    def raise_not_file(self) -> NoReturn | None:
        """路径目标不是文件或不存在时抛出 ResourceNotFileError 异常"""
        if not self.is_file:
            raise ResourceNotFileError(self.path)

    def raise_not_dir(self) -> NoReturn | None:
        """路径目标不是文件夹或不存在时抛出 ResourceNotFolderError 异常"""
        if not self.is_dir:
            raise ResourceNotFolderError(self.path)

    @staticmethod
    def check_directory[**P, R, ST: 'BaseResource'](
            func: Callable[Concatenate[ST, P], R],
    ) -> Callable[Concatenate[ST, P], R]:
        """装饰一个方法, 需要实例 path 为文件夹时才能运行"""

        @wraps(func)
        def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            if self.path.exists() and self.path.is_dir():
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFolderError(self.path)

        return _wrapper

    @staticmethod
    def check_file[**P, R, ST: 'BaseResource'](
            func: Callable[Concatenate[ST, P], R],
    ) -> Callable[Concatenate[ST, P], R]:
        """装饰一个方法, 需要实例 path 为文件时才能运行"""

        @wraps(func)
        def _wrapper(self: ST, *args: P.args, **kwargs: P.kwargs) -> R:
            if self.path.exists() and self.path.is_file():
                return func(self, *args, **kwargs)
            elif not self.path.exists():
                if not self.path.parent.exists():
                    Path.mkdir(self.path.parent, parents=True)
                return func(self, *args, **kwargs)
            else:
                raise ResourceNotFileError(self.path)

        return _wrapper

    def ensure_parent_path(self, *, exist_ok: bool = False) -> None:
        """检查父路径并确保其存在"""
        if not self.path.parent.exists():
            Path.mkdir(self.path.parent, parents=True, exist_ok=exist_ok)

    @property
    def parent(self) -> Self:
        """返回逻辑父路径"""
        self.ensure_parent_path()
        return self.init_from_path(path=self.path.parent)

    @property
    def resolve_path(self) -> str:
        """将路径绝对化，解析任何符号链接"""
        return self.path.resolve().as_posix()

    @property
    @check_file
    def file_uri(self) -> str:
        """将路径表示为 file URI"""
        return self.path.resolve().as_uri()

    @overload
    def open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: str | None = None,
            **kwargs
    ) -> ContextManager['TextIOWrapper']:
        ...

    @overload
    def open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: str | None = None,
            **kwargs
    ) -> ContextManager['FileIO']:
        ...

    @contextmanager
    @check_file
    def open(self, mode, encoding: str | None = None, **kwargs) -> Generator[IO, Any, None]:
        """返回文件 handle"""
        with self.path.open(mode=mode, encoding=encoding, **kwargs) as _fh:
            yield _fh

    @overload
    def async_open(
            self,
            mode: Literal['r', 'w', 'x', 'a', 'r+', 'w+', 'x+', 'a+'],
            encoding: str | None = None,
            **kwargs
    ) -> AsyncContextManager['AsyncTextIOWrapper']:
        ...

    @overload
    def async_open(
            self,
            mode: Literal['rb', 'wb', 'xb', 'ab', 'rb+', 'wb+', 'xb+', 'ab+'],
            encoding: str | None = None,
            **kwargs
    ) -> AsyncContextManager['AsyncFileIO']:
        ...

    @asynccontextmanager
    @check_file
    async def async_open(self, mode, encoding: str | None = None, **kwargs):
        """返回文件 async handle"""
        async with aiofiles.open(file=self.path, mode=mode, encoding=encoding, **kwargs) as _afh:
            yield _afh

    @check_directory
    def list_all_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表"""
        file_list = []
        for dir_path, _, file_names in self.path.walk():
            if file_names:
                for file_name in file_names:
                    file_list.append(self.init_from_path(dir_path.joinpath(file_name)))
        return file_list

    @check_directory
    def list_current_files(self) -> list[Self]:
        """遍历文件夹内所有文件并返回文件列表(不包含子目录)"""
        file_list = []
        for file_path in self.path.iterdir():
            file = self.init_from_path(file_path)
            if file.is_file:
                file_list.append(file)
        return file_list

    @check_directory
    def iter_all_files(self) -> Generator[Self, Any, None]:
        """遍历文件夹内所有文件"""
        for dir_path, _, file_names in self.path.walk():
            if file_names:
                for file_name in file_names:
                    yield self.init_from_path(dir_path.joinpath(file_name))

    @check_directory
    def iter_current_files(self) -> Generator[Self, Any, None]:
        """遍历文件夹内所有文件(不包含子目录)"""
        for file_path in self.path.iterdir():
            file = self.init_from_path(file_path)
            if file.is_file:
                yield file

    @check_file
    def remove(self, *, missing_ok=True) -> None:
        """移除此文件或符号链接"""
        return self.path.unlink(missing_ok=missing_ok)

    @check_file
    async def get_hosting_path(self, *, ttl_delta: int = 0) -> str:
        """获取文件托管路径, 已注册文件托管服务时返回文件 URL, 未启用时返回文件本地路径"""
        if self._host_protocol is None:
            return self.resolve_path
        else:
            return await self._host_protocol(self).get_hosting_file_path(ttl_delta=ttl_delta)


class AnyResource(BaseResource):
    """任意位置资源文件"""

    def __init__(self, path: str | Path, /, *args: str):
        self.path = Path(path).joinpath(*args)


class LogFileResource(BaseResource):
    """日志文件"""

    def __init__(self, *args: str):
        self.timestamp = datetime.now()
        self.path = _LOG_FOLDER.joinpath(self.timestamp.strftime('%Y-%m'))

    @property
    def debug(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-DEBUG.log').path

    @property
    def info(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-INFO.log').path

    @property
    def warring(self) -> Path:
        return self(f'{self.timestamp.strftime('%Y%m%d-%H%M%S')}-WARRING.log').path

    @property
    def error(self) -> Path:
        return self(f'{datetime.now().strftime('%Y%m%d-%H%M%S')}-ERROR.log').path


class StaticResource(BaseResource):
    """静态资源文件"""

    def __init__(self, *args: str):
        self.path = _STATIC_RESOURCE_FOLDER.joinpath(*args)


class TemporaryResource(BaseResource):
    """运行时产生的的可随时清理的缓存/临时文件"""

    def __init__(self, *args: str):
        self.path = _TEMPORARY_RESOURCE_FOLDER.joinpath(*args)


__all__ = [
    'AnyResource',
    'BaseResource',
    'BaseResourceHostProtocol',
    'LogFileResource',
    'StaticResource',
    'TemporaryResource',
    'ResourceNotFolderError',
    'ResourceNotFileError',
]
