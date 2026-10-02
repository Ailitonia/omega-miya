"""
@Author         : Ailitonia
@Date           : 2026/9/20 19:02
@FileName       : test_007_zip_utils
@Project        : omega-miya
@Description    : 压缩文件创建工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import io
import re
import zipfile
from pathlib import PurePosixPath
from types import SimpleNamespace
from typing import Any, ClassVar, NoReturn, Self

import py7zr
import pytest

from tests.utils import rebind_module_namespace

_RealZipFile = zipfile.ZipFile


class _MemoryInputResource:
    """鸭子类型的待压缩文件替身, 全内存"""

    def __init__(self, resolve_path: str, *, is_file: bool = True) -> None:
        self._resolve_path = resolve_path
        self._is_file = is_file

    @property
    def name(self) -> str:
        return PurePosixPath(self._resolve_path).name

    @property
    def is_file(self) -> bool:
        return self._is_file

    @property
    def resolve_path(self) -> str:
        return self._resolve_path


class _MemoryTargetResource:
    """鸭子类型的目标压缩文件替身, 记录操作, 全内存"""

    replace_error: ClassVar[OSError | None] = None
    """类级注入: 非 None 时 replace 抛出该异常, 模拟 Path.replace 的 OSError 失败"""

    def __init__(self, name: str, *, exists: bool = False) -> None:
        self._path = PurePosixPath('/memory').joinpath(name)
        self._exists = exists
        self.parent_ensured = False
        self.children: list[_MemoryTargetResource] = []
        self.replaced_to: list[Any] = []
        self.removed_calls: list[bool] = []

    @property
    def path(self) -> PurePosixPath:
        return self._path

    @property
    def name(self) -> str:
        return self._path.name

    @property
    def suffix(self) -> str:
        return self._path.suffix

    @property
    def is_file(self) -> bool:
        return self._exists

    @property
    def resolve_path(self) -> str:
        return self._path.as_posix()

    def with_suffix(self, suffix: str) -> Self:
        """模拟 BaseResource.with_suffix 的同目录派生语义, 并记录派生出的子替身"""
        child = _MemoryTargetResource(self._path.with_suffix(suffix).name)
        self.children.append(child)
        return child

    def ensure_parent_path(self, **kwargs: Any) -> None:
        self.parent_ensured = True

    def replace(self, target: Any) -> Self:
        """记录替换调用; 不模拟 @check_file(真实流程中 ZipFile 打开即创建临时文件, 校验必然通过)"""
        if type(self).replace_error is not None:
            raise type(self).replace_error
        self.replaced_to.append(target)
        return self

    def remove(self, *, missing_ok: bool = True) -> None:
        self.removed_calls.append(missing_ok)
        self._exists = False


class _MemoryDirResource:
    """鸭子类型的目录资源替身"""

    def __init__(self, *, is_dir: bool) -> None:
        self._is_dir = is_dir

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    def __call__(self, name: str) -> _MemoryTargetResource:
        return _MemoryTargetResource(name)

    def raise_not_dir(self) -> NoReturn | None:
        from src.resource import ResourceNotFolderError
        if not self.is_dir:
            raise ResourceNotFolderError(PurePosixPath())


class _BytesIOZipFile:
    """替换 zipfile.ZipFile: 写入 BytesIO 并记录调用"""

    created: ClassVar[list['_BytesIOZipFile']] = []

    def __init__(self, file: Any, mode: str = 'r', compression: int | None = None, **kwargs: Any) -> None:
        type(self).created.append(self)
        self.file_arg = file
        self.mode = mode
        self.compression = compression
        self.buffer = io.BytesIO()
        self.written: list[str] = []
        self._zf = _RealZipFile(self.buffer, mode='w', compression=zipfile.ZIP_STORED) if mode == 'w' else None

    def write(self, filename: Any, arcname: str | None = None, **kwargs: Any) -> None:
        self.written.append(arcname)
        if self._zf is not None:
            self._zf.writestr(arcname, b'fake-content')

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        if self._zf is not None:
            self._zf.close()
        return False


class _BytesIOZipFileRaising(_BytesIOZipFile):
    """write 时抛异常的 ZipFile 替身, 模拟写入中途失败"""

    def write(self, filename: Any, arcname: str | None = None, **kwargs: Any) -> NoReturn:
        raise OSError('disk full')


class _FakeSevenZipFile:
    """替换 py7zr.SevenZipFile: 记录调用"""

    created: ClassVar[list['_FakeSevenZipFile']] = []

    def __init__(self, target: Any, mode: str = 'r', password: str | None = None, **kwargs: Any) -> None:
        type(self).created.append(self)
        self.target = target
        self.mode = mode
        self.password = password
        self.encrypted_header: bool | None = None
        self.written: list[str] = []

    def set_encrypted_header(self, flag: bool) -> None:
        self.encrypted_header = flag

    def write(self, path: Any, arcname: str | None = None, **kwargs: Any) -> None:
        self.written.append(arcname)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


class _FakeSevenZipFileRaising(_FakeSevenZipFile):
    """write 时抛异常的 SevenZipFile 替身, 模拟写入中途失败"""

    def write(self, path: Any, arcname: str | None = None, **kwargs: Any) -> NoReturn:
        raise OSError('disk full')


@pytest.fixture
def reset_fakes() -> Any:
    _BytesIOZipFile.created.clear()
    _FakeSevenZipFile.created.clear()
    _MemoryTargetResource.replace_error = None
    yield
    _BytesIOZipFile.created.clear()
    _FakeSevenZipFile.created.clear()
    _MemoryTargetResource.replace_error = None


def _patch_archive_backends(
        monkeypatch: pytest.MonkeyPatch,
        *,
        zip_file_cls: type | None = None,
        seven_zip_file_cls: type | None = None,
) -> None:
    """以拷贝命名空间重绑定 zip_utils 模块内的 zipfile/py7zr 名字, 不污染进程级共享库模块"""
    import src.utils.zip_utils as zip_utils_module

    if zip_file_cls is not None:
        rebind_module_namespace(monkeypatch, zip_utils_module, 'zipfile', ZipFile=zip_file_cls)
    if seven_zip_file_cls is not None:
        rebind_module_namespace(monkeypatch, zip_utils_module, 'py7zr', SevenZipFile=seven_zip_file_cls)


def _install_backend(monkeypatch: pytest.MonkeyPatch, backend: str, *, raising: bool = False) -> SimpleNamespace:
    """安装指定归档后端的伪实现, 返回调用上下文(方法名/目标文件名/创建记录列表)"""
    if backend == 'zip':
        _patch_archive_backends(
            monkeypatch, zip_file_cls=_BytesIOZipFileRaising if raising else _BytesIOZipFile,
        )
        return SimpleNamespace(method='create_zip', file_name='test.zip', created=_BytesIOZipFile.created)
    _patch_archive_backends(
        monkeypatch, seven_zip_file_cls=_FakeSevenZipFileRaising if raising else _FakeSevenZipFile,
    )
    return SimpleNamespace(method='create_7z', file_name='test.7z', created=_FakeSevenZipFile.created)


def _make_zip_utils(file_name: str, *, overwrite: bool = True, target_exists: bool = False):
    from src.utils.zip_utils import ZipUtils

    zu = ZipUtils(file_name, overwrite=overwrite)
    zu.file = _MemoryTargetResource(PurePosixPath(file_name).name, exists=target_exists)
    return zu


class TestCreateZipBaseline:
    """create_zip 现有正确行为"""

    async def test_writes_all_files_with_basename_arcname(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        result = await zu.create_zip([
            _MemoryInputResource('/mem/sub/a.txt'),
            _MemoryInputResource('/mem/b.txt'),
        ])
        assert result is zu.file
        assert _BytesIOZipFile.created[-1].written == ['a.txt', 'b.txt']
        assert zu.file.children[-1].replaced_to == [zu.file.path]

    async def test_produces_valid_in_memory_zip_readable_via_bytesio(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        _buffer = _BytesIOZipFile.created[-1].buffer
        _buffer.seek(0)
        with _RealZipFile(_buffer) as _zf:
            assert _zf.namelist() == ['a.txt']
            assert _zf.read('a.txt') == b'fake-content'

    async def test_skips_archive_itself(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([
            _MemoryInputResource(zu.file.resolve_path),
            _MemoryInputResource('/mem/a.txt'),
        ])
        assert _BytesIOZipFile.created[-1].written == ['a.txt']

    async def test_overwrite_false_existing_target_raises(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', overwrite=False, target_exists=True)
        with pytest.raises(RuntimeError, match='already exists'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert not _BytesIOZipFile.created
        assert not zu.file.children

    async def test_overwrite_true_replaces_existing_atomically(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', overwrite=True, target_exists=True)
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.parent_ensured
        assert _BytesIOZipFile.created[-1].written == ['a.txt']
        assert len(zu.file.children) == 1
        _tmp = zu.file.children[-1]
        assert _tmp.replaced_to == [zu.file.path]
        assert not _tmp.removed_calls
        _stem = PurePosixPath(zu.file.name).stem
        assert re.fullmatch(rf'{_stem}\.[0-9a-f]{{32}}\.tmp', _tmp.name)

    async def test_compression_passthrough(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=zipfile.ZIP_DEFLATED)
        assert _BytesIOZipFile.created[-1].compression == zipfile.ZIP_DEFLATED

    async def test_default_compression_from_config(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        from src.utils.zip_utils.config import zip_utils_config

        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert _BytesIOZipFile.created[-1].compression == zip_utils_config.zip_utils_default_zip_compression


class TestCreate7zBaseline:
    """create_7z 现有正确行为"""

    async def test_writes_files_with_password(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, seven_zip_file_cls=_FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        result = await zu.create_7z([_MemoryInputResource('/mem/a.txt')], password='secret')
        assert result is zu.file
        _inst = _FakeSevenZipFile.created[-1]
        assert _inst.written == ['a.txt']
        assert _inst.password == 'secret'
        assert _inst.encrypted_header is True
        assert zu.file.children[-1].replaced_to == [zu.file.path]

    async def test_no_password_no_encrypted_header(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, seven_zip_file_cls=_FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        await zu.create_7z([_MemoryInputResource('/mem/a.txt')])
        assert _FakeSevenZipFile.created[-1].password is None
        assert _FakeSevenZipFile.created[-1].encrypted_header is None


class TestValidationBeforeWrite:
    """校验阶段为纯校验, 校验失败时不创建归档且不替换既有目标文件"""

    @pytest.mark.parametrize(
        ('backend', 'file_name'),
        [('zip', 'test.txt'), ('7z', 'test.zip')],
        ids=['zip', '7z'],
    )
    async def test_wrong_suffix_raises_value_error(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, backend: str, file_name: str,
    ):
        ctx = _install_backend(monkeypatch, backend)
        zu = _make_zip_utils(file_name)
        with pytest.raises(ValueError, match='suffix'):
            await getattr(zu, ctx.method)([_MemoryInputResource('/mem/a.txt')])
        assert not ctx.created
        assert not zu.file.children

    async def test_wrong_suffix_7z_call_preserves_existing_zip(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, seven_zip_file_cls=_FakeSevenZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_7z([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.is_file
        assert not zu.file.children

    async def test_wrong_suffix_zip_call_preserves_existing_7z(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.7z', target_exists=True)
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.is_file
        assert not zu.file.children

    async def test_fresh_target_written_via_replace(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=False)
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.parent_ensured
        assert len(zu.file.children) == 1
        assert zu.file.children[-1].replaced_to == [zu.file.path]


class TestAtomicWrite:
    """原子写入, 写入失败清理临时文件且不影响既有目标文件"""

    @pytest.mark.parametrize('backend', ['zip', '7z'])
    async def test_write_failure_cleans_tmp_and_skips_replace(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, backend: str,
    ):
        ctx = _install_backend(monkeypatch, backend, raising=True)
        zu = _make_zip_utils(ctx.file_name, target_exists=True)
        with pytest.raises(OSError, match='disk full'):
            await getattr(zu, ctx.method)([_MemoryInputResource('/mem/a.txt')])
        _tmp = zu.file.children[-1]
        assert not _tmp.replaced_to
        assert _tmp.removed_calls == [True]
        assert zu.file.is_file

    async def test_replace_failure_cleans_tmp(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        _MemoryTargetResource.replace_error = OSError('target locked')
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(RuntimeError, match='写入压缩文件失败') as exc_info:
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert isinstance(exc_info.value.__cause__, OSError)
        assert str(exc_info.value.__cause__) == 'target locked'
        _tmp = zu.file.children[-1]
        assert not _tmp.replaced_to
        assert _tmp.removed_calls == [True]
        assert zu.file.is_file

    async def test_tmp_file_in_target_directory(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        _tmp = _BytesIOZipFile.created[-1].file_arg
        assert PurePosixPath(_tmp).parent == PurePosixPath(zu.file.resolve_path).parent


class TestDuplicateArcnames:
    """待压缩文件重名(arcname 冲突)时报错而非写入重复条目"""

    @pytest.mark.parametrize('backend', ['zip', '7z'])
    async def test_duplicate_names_raises(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, backend: str):
        ctx = _install_backend(monkeypatch, backend)
        zu = _make_zip_utils(ctx.file_name)
        with pytest.raises(ValueError, match='Duplicate'):
            await getattr(zu, ctx.method)([
                _MemoryInputResource('/mem/x/a.txt'),
                _MemoryInputResource('/mem/y/a.txt'),
            ])
        assert not ctx.created
        assert not zu.file.children

    async def test_duplicate_failure_preserves_existing_target(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='Duplicate'):
            await zu.create_zip([
                _MemoryInputResource('/mem/x/a.txt'),
                _MemoryInputResource('/mem/y/a.txt'),
            ])
        assert zu.file.is_file
        assert not zu.file.children


class TestEmptyFiles:
    """有效待压缩文件为空时报错而非生成空压缩包"""

    @pytest.mark.parametrize('self_only', [False, True], ids=['empty', 'self-only'])
    async def test_no_effective_files_raises(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, self_only: bool,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        files = [_MemoryInputResource(zu.file.resolve_path)] if self_only else []
        with pytest.raises(ValueError, match='No files'):
            await zu.create_zip(files)
        assert not _BytesIOZipFile.created
        assert not zu.file.children


class TestMissingInputRaises:
    """待压缩文件缺失或非文件时报错而非静默跳过"""

    @pytest.mark.parametrize('backend', ['zip', '7z'])
    async def test_missing_input_raises_value_error(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, backend: str,
    ):
        ctx = _install_backend(monkeypatch, backend)
        zu = _make_zip_utils(ctx.file_name)
        with pytest.raises(ValueError, match='not found'):
            await getattr(zu, ctx.method)([
                _MemoryInputResource('/mem/a.txt'),
                _MemoryInputResource('/mem/missing.txt', is_file=False),
            ])
        assert not ctx.created
        assert not zu.file.children

    async def test_missing_input_failure_preserves_existing_target(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='not found'):
            await zu.create_zip([_MemoryInputResource('/mem/missing.txt', is_file=False)])
        assert zu.file.is_file
        assert not zu.file.children

    async def test_self_reference_not_treated_as_missing(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource(zu.file.resolve_path), _MemoryInputResource('/mem/a.txt')])
        assert _BytesIOZipFile.created[-1].written == ['a.txt']


class TestInitValidation:
    """构造参数校验"""

    def test_folder_not_dir_raises_value_error(self):
        from src.resource import ResourceNotFolderError
        from src.utils.zip_utils import ZipUtils

        with pytest.raises(ResourceNotFolderError, match='is not a directory'):
            ZipUtils('test.zip', folder=_MemoryDirResource(is_dir=False))

    def test_folder_dir_accepted(self):
        from src.utils.zip_utils import ZipUtils

        zu = ZipUtils('test.zip', folder=_MemoryDirResource(is_dir=True))
        assert zu.file.name == 'test.zip'

    def test_plain_file_name_accepted(self):
        from src.utils.zip_utils import ZipUtils

        zu = ZipUtils('test.zip')
        assert zu.file.name == 'test.zip'


class TestParameterSemantics:
    """compression 参数语义与校验、后缀大小写、空字符串密码"""

    async def test_invalid_compression_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=999)
        assert not _BytesIOZipFile.created
        assert not zu.file.children

    async def test_invalid_compression_failure_preserves_existing_target(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=999)
        assert zu.file.is_file
        assert not zu.file.children

    async def test_invalid_config_default_compression_raises_before_write(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        from src.utils.zip_utils.config import zip_utils_config

        monkeypatch.setattr(zip_utils_config, 'zip_utils_default_zip_compression', 999)
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.is_file
        assert not zu.file.children

    async def test_valid_compression_methods_accepted(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, zip_file_cls=_BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        for _method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2):
            _BytesIOZipFile.created.clear()
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=_method)
            assert _BytesIOZipFile.created[-1].compression == _method

    @pytest.mark.parametrize('backend', ['zip', '7z'])
    async def test_uppercase_suffix_accepted(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None, backend: str):
        ctx = _install_backend(monkeypatch, backend)
        zu = _make_zip_utils(ctx.file_name.upper())
        await getattr(zu, ctx.method)([_MemoryInputResource('/mem/a.txt')])
        assert ctx.created[-1].written == ['a.txt']

    async def test_empty_password_treated_as_none(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        _patch_archive_backends(monkeypatch, seven_zip_file_cls=_FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        await zu.create_7z([_MemoryInputResource('/mem/a.txt')], password='')
        assert _FakeSevenZipFile.created[-1].password is None
        assert _FakeSevenZipFile.created[-1].encrypted_header is None


class TestZipUtilsConfig:
    """ZipUtilsConfig 配置"""

    def test_defaults(self):
        from src.utils.zip_utils.config import ZipUtilsConfig

        _config = ZipUtilsConfig()
        assert _config.zip_utils_default_zip_compression == zipfile.ZIP_STORED
        assert _config.zip_utils_default_output_folder_name == 'zip_utils'

    def test_default_output_folder(self):
        from src.resource import TemporaryResource
        from src.utils.zip_utils.config import ZipUtilsConfig

        _folder = ZipUtilsConfig().default_output_folder
        assert isinstance(_folder, TemporaryResource)
        assert _folder.path.name == 'zip_utils'

    def test_extra_ignored(self):
        from src.utils.zip_utils.config import ZipUtilsConfig

        assert ZipUtilsConfig.model_validate({'unknown_field': 1}) is not None


class TestModuleExports:
    """模块导出完整性"""

    def test_all_exports(self):
        from src.utils import zip_utils

        assert set(zip_utils.__all__) == {'ZipUtils'}
        assert zip_utils.ZipUtils is not None


class TestPatchIsolation:
    """patch 隔离性: 重绑定 zip_utils 命名空间不得污染进程级共享库模块"""

    async def test_patch_does_not_pollute_global_modules(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        _patch_archive_backends(
            monkeypatch, zip_file_cls=_BytesIOZipFile, seven_zip_file_cls=_FakeSevenZipFile,
        )

        assert zipfile.ZipFile is _RealZipFile
        assert py7zr.SevenZipFile is not _FakeSevenZipFile
