"""
@Author         : Ailitonia
@Date           : 2026/9/20 19:02
@FileName       : test_007_zip_utils
@Project        : omega-miya
@Description    : 压缩文件创建工具单元测试
@GitHub         : https://github.com/Ailitria
@Software       : PyCharm
"""

import io
import zipfile
from pathlib import PurePosixPath
from typing import Any, ClassVar, NoReturn, Self

import py7zr
import pytest

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

    def __init__(self, name: str, *, exists: bool = False) -> None:
        self._path = PurePosixPath('/memory').joinpath(name)
        self._exists = exists
        self.removed = False
        self.parent_ensured = False

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

    def ensure_parent_path(self, **kwargs: Any) -> None:
        self.parent_ensured = True

    def remove(self, **kwargs: Any) -> None:
        self.removed = True
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


@pytest.fixture
def reset_fakes() -> Any:
    _BytesIOZipFile.created.clear()
    _FakeSevenZipFile.created.clear()
    yield
    _BytesIOZipFile.created.clear()
    _FakeSevenZipFile.created.clear()


def _make_zip_utils(file_name: str, *, overwrite: bool = True, target_exists: bool = False):
    from src.utils.zip_utils import ZipUtils

    zu = ZipUtils(file_name, overwrite=overwrite)
    zu.file = _MemoryTargetResource(PurePosixPath(file_name).name, exists=target_exists)
    return zu


class TestCreateZipBaseline:
    """create_zip 现有正确行为"""

    async def test_writes_all_files_with_basename_arcname(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        result = await zu.create_zip([
            _MemoryInputResource('/mem/sub/a.txt'),
            _MemoryInputResource('/mem/b.txt'),
        ])
        assert result is zu.file
        assert _BytesIOZipFile.created[-1].written == ['a.txt', 'b.txt']

    async def test_produces_valid_in_memory_zip_readable_via_bytesio(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        _buffer = _BytesIOZipFile.created[-1].buffer
        _buffer.seek(0)
        with _RealZipFile(_buffer) as _zf:
            assert _zf.namelist() == ['a.txt']
            assert _zf.read('a.txt') == b'fake-content'

    async def test_skips_archive_itself(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([
            _MemoryInputResource(zu.file.resolve_path),
            _MemoryInputResource('/mem/a.txt'),
        ])
        assert _BytesIOZipFile.created[-1].written == ['a.txt']

    async def test_wrong_suffix_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.txt')
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert not _BytesIOZipFile.created

    async def test_overwrite_false_existing_target_raises(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', overwrite=False, target_exists=True)
        with pytest.raises(RuntimeError, match='already exists'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert not zu.file.removed

    async def test_overwrite_true_removes_existing_then_writes(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', overwrite=True, target_exists=True)
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.removed
        assert zu.file.parent_ensured
        assert _BytesIOZipFile.created[-1].written == ['a.txt']

    async def test_compression_passthrough(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=zipfile.ZIP_DEFLATED)
        assert _BytesIOZipFile.created[-1].compression == zipfile.ZIP_DEFLATED

    async def test_default_compression_from_config(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        from src.utils.zip_utils.config import zip_utils_config

        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert _BytesIOZipFile.created[-1].compression == zip_utils_config.zip_utils_default_zip_compression


class TestCreate7zBaseline:
    """create_7z 现有正确行为"""

    async def test_writes_files_with_password(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(py7zr, 'SevenZipFile', _FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        result = await zu.create_7z([_MemoryInputResource('/mem/a.txt')], password='secret')
        assert result is zu.file
        _inst = _FakeSevenZipFile.created[-1]
        assert _inst.written == ['a.txt']
        assert _inst.password == 'secret'
        assert _inst.encrypted_header is True

    async def test_no_password_no_encrypted_header(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(py7zr, 'SevenZipFile', _FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        await zu.create_7z([_MemoryInputResource('/mem/a.txt')])
        assert _FakeSevenZipFile.created[-1].password is None
        assert _FakeSevenZipFile.created[-1].encrypted_header is None

    async def test_wrong_suffix_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(py7zr, 'SevenZipFile', _FakeSevenZipFile)
        zu = _make_zip_utils('test.zip')
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_7z([_MemoryInputResource('/mem/a.txt')])
        assert not _FakeSevenZipFile.created


class TestFixValidationBeforeDelete:
    """H1: 任何校验失败时不得删除既有目标文件"""

    async def test_wrong_suffix_7z_call_preserves_existing_zip(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(py7zr, 'SevenZipFile', _FakeSevenZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_7z([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.removed is False

    async def test_wrong_suffix_zip_call_preserves_existing_7z(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.7z', target_exists=True)
        with pytest.raises(ValueError, match='suffix'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.removed is False

    async def test_no_remove_when_target_missing(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=False)
        await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.removed is False
        assert zu.file.parent_ensured


class TestFixMissingInputRaises:
    """M1: 待压缩文件缺失或非文件时报错而非静默跳过"""

    async def test_missing_input_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        with pytest.raises(ValueError, match='not found'):
            await zu.create_zip([
                _MemoryInputResource('/mem/a.txt'),
                _MemoryInputResource('/mem/missing.txt', is_file=False),
            ])
        assert not _BytesIOZipFile.created

    async def test_missing_input_7z_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(py7zr, 'SevenZipFile', _FakeSevenZipFile)
        zu = _make_zip_utils('test.7z')
        with pytest.raises(ValueError, match='not found'):
            await zu.create_7z([_MemoryInputResource('/mem/missing.src', is_file=False)])

    async def test_missing_input_failure_preserves_existing_target(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='not found'):
            await zu.create_zip([_MemoryInputResource('/mem/missing.txt', is_file=False)])
        assert zu.file.removed is False

    async def test_self_reference_not_treated_as_missing(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        await zu.create_zip([_MemoryInputResource(zu.file.resolve_path), _MemoryInputResource('/mem/a.txt')])
        assert _BytesIOZipFile.created[-1].written == ['a.txt']


class TestFixInitValidation:
    """M2/M3: 构造参数校验"""

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


class TestLowFixes:
    """L1: compression 参数语义与校验"""

    async def test_invalid_compression_raises_value_error(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=999)

    async def test_invalid_compression_failure_preserves_existing_target(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=999)
        assert zu.file.removed is False

    async def test_invalid_config_default_compression_raises_before_delete(
            self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None,
    ):
        from src.utils.zip_utils.config import zip_utils_config

        monkeypatch.setattr(zip_utils_config, 'zip_utils_default_zip_compression', 999)
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip', target_exists=True)
        with pytest.raises(ValueError, match='compression'):
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')])
        assert zu.file.removed is False

    async def test_valid_compression_methods_accepted(self, monkeypatch: pytest.MonkeyPatch, reset_fakes: None):
        monkeypatch.setattr(zipfile, 'ZipFile', _BytesIOZipFile)
        zu = _make_zip_utils('test.zip')
        for _method in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED, zipfile.ZIP_LZMA, zipfile.ZIP_BZIP2):
            _BytesIOZipFile.created.clear()
            await zu.create_zip([_MemoryInputResource('/mem/a.txt')], compression=_method)
            assert _BytesIOZipFile.created[-1].compression == _method


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
