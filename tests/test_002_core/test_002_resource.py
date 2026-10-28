"""
@Author         : Ailitonia
@Date           : 2026/9/3 19:52
@FileName       : test_002_resource
@Project        : omega-miya
@Description    : src.resource 模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import hashlib
import string
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

_SampleFileFactory = Callable[[str, bytes | str], Path]
"""sample_file fixture 返回的造文件工厂签名"""

_SYNC_TEXT_CONTENT = 'hello'
"""同步文本往返写入内容"""
_ASYNC_TEXT_CONTENT = 'async hello'
"""异步文本往返写入内容"""
_BINARY_CONTENT = b'\x00\x01'
"""二进制往返写入内容"""
_NESTED_FILE_CONTENT = 'x'
"""深层路径写入内容"""


@pytest.fixture
def fixed_datetime(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """将 src.resource 模块内的 datetime 替换为固定时间, 消除跨月/跨秒竞态"""
    import src.resource

    fixed = datetime(2026, 2, 3, 4, 5, 6)

    class _FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None) -> datetime:
            return fixed

    monkeypatch.setattr(src.resource, 'datetime', _FixedDatetime)
    return fixed


@pytest.fixture
def sample_tree(tmp_path: Path) -> Path:
    """构建测试用目录结构: tmp_path/a.txt + tmp_path/sub/b.txt"""
    tmp_path.joinpath('a.txt').write_text('a', encoding='utf-8')
    tmp_path.joinpath('sub').mkdir()
    tmp_path.joinpath('sub', 'b.txt').write_text('bb', encoding='utf-8')
    return tmp_path


@pytest.fixture
def sample_file(tmp_path: Path) -> _SampleFileFactory:
    """造文件工厂: 在 tmp_path 下创建指定名称/内容的文件并返回其路径"""

    def _make_file(name: str, content: bytes | str) -> Path:
        file = tmp_path / name
        if isinstance(content, bytes):
            file.write_bytes(content)
        else:
            file.write_text(content, encoding='utf-8')
        return file

    return _make_file


class TestExceptions:
    """资源异常类测试"""

    @pytest.mark.parametrize(
        ('exc_class_name', 'sub_path', 'message_fragment'),
        [
            ('ResourceNotFileError', 'f.txt', 'is not a file'),
            ('ResourceNotFolderError', 'd', 'is not a directory'),
        ],
    )
    def test_not_file_or_folder_error(self, tmp_path: Path, exc_class_name: str, sub_path: str, message_fragment: str):
        import src.resource
        from src.exception import LocalSourceException, OmegaException

        exc_class = getattr(src.resource, exc_class_name)
        exc = exc_class(tmp_path / sub_path)
        assert isinstance(exc, LocalSourceException)
        assert isinstance(exc, OmegaException)
        assert exc.path == tmp_path / sub_path
        assert exc.path.as_posix() in exc.message
        assert message_fragment in exc.message
        assert exc_class_name in repr(exc)
        assert str(exc) == repr(exc)

    def test_exception_with_str_path(self):
        """LocalSourceException 兼容 str 构造, 内部规范化为 Path"""
        from src.resource import ResourceNotFileError, ResourceNotFolderError

        file_exc = ResourceNotFileError('some/missing.txt')
        assert file_exc.path == Path('some/missing.txt')
        assert 'some/missing.txt' in file_exc.message
        assert 'ResourceNotFileError' in repr(file_exc)

        folder_exc = ResourceNotFolderError('some/missing_dir')
        assert folder_exc.path == Path('some/missing_dir')
        assert 'some/missing_dir' in folder_exc.message
        assert 'ResourceNotFolderError' in repr(folder_exc)


class TestModuleContract:
    """模块导出契约与模块级常量测试"""

    def test_all_exports(self):
        import src.resource

        assert src.resource.__all__ == [
            'AnyResource',
            'BaseResource',
            'BaseResourceHostProtocol',
            'HostingPathType',
            'LogFileResource',
            'StaticResource',
            'TemporaryResource',
            'ResourceNotFolderError',
            'ResourceNotFileError',
            'ResourcePathOutOfRootError',
            'clean_ascii_valid_dirname',
            'clean_ascii_valid_filename',
        ]

    def test_root_path_derived_from_module_file(self):
        """项目根目录由模块文件位置推导, 不依赖进程启动方式"""
        import src.resource

        root_path = getattr(src.resource, '__ROOT_PATH')
        assert root_path == Path(src.resource.__file__).resolve().parent.parent

    def test_root_folders(self):
        import src.resource

        # 注意: 类体中直接访问 src.resource.__ROOT_PATH 会触发名称改写, 需用 getattr
        root_path = getattr(src.resource, '__ROOT_PATH')
        assert src.resource._LOG_FOLDER == root_path.joinpath('log')
        assert src.resource._STATIC_RESOURCE_FOLDER == root_path.joinpath('static')
        assert src.resource._TEMPORARY_RESOURCE_FOLDER == root_path.joinpath('.tmp')


class TestAbstractClasses:
    """抽象基类测试"""

    def test_base_resource_cannot_instantiate(self):
        from src.resource import BaseResource

        with pytest.raises(TypeError):
            BaseResource()

    def test_base_resource_init_body_raises(self):
        from src.resource import BaseResource

        with pytest.raises(NotImplementedError):
            BaseResource.__init__(object())

    def test_host_protocol_cannot_instantiate_without_implementation(self):
        from src.resource import AnyResource, BaseResourceHostProtocol

        class _IncompleteProtocol(BaseResourceHostProtocol):
            pass

        with pytest.raises(TypeError):
            _IncompleteProtocol(AnyResource('.'))


class TestConstructors:
    """各资源类构造语义测试"""

    def test_any_resource_from_str(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(str(tmp_path)).path == tmp_path

    def test_any_resource_from_path(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path).path == tmp_path

    def test_any_resource_joins_args(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path, 'a', 'b.txt').path == tmp_path / 'a' / 'b.txt'

    def test_static_resource_root(self):
        import src.resource
        from src.resource import StaticResource

        assert StaticResource('a', 'b.txt').path == src.resource._STATIC_RESOURCE_FOLDER.joinpath('a', 'b.txt')
        assert StaticResource().path == src.resource._STATIC_RESOURCE_FOLDER

    def test_temporary_resource_root(self):
        import src.resource
        from src.resource import TemporaryResource

        assert TemporaryResource('a', 'b.txt').path == src.resource._TEMPORARY_RESOURCE_FOLDER.joinpath('a', 'b.txt')
        assert TemporaryResource().path == src.resource._TEMPORARY_RESOURCE_FOLDER

    def test_log_resource_month_subdir(self, fixed_datetime: datetime):
        import src.resource
        from src.resource import LogFileResource

        resource = LogFileResource()
        assert resource.path == src.resource._LOG_FOLDER.joinpath(fixed_datetime.strftime('%Y-%m'))
        assert resource.timestamp == fixed_datetime


class TestLogFileResource:
    """LogFileResource 日志文件属性测试(固定时间)"""

    @pytest.mark.parametrize(
        ('attr', 'level'),
        [
            ('debug', 'DEBUG'),
            ('info', 'INFO'),
            ('warning', 'WARNING'),
            ('error', 'ERROR'),
        ],
    )
    def test_level_log_file(self, fixed_datetime: datetime, attr: str, level: str):
        import src.resource
        from src.resource import LogFileResource

        path = getattr(LogFileResource(), attr)
        assert isinstance(path, Path)
        assert path == src.resource._LOG_FOLDER.joinpath('2026-02', f'20260203-040506-{level}.log')

    def test_error_uses_instance_timestamp(self, monkeypatch: pytest.MonkeyPatch):
        """error 属性应与其他属性一致使用实例构造时的时间戳, 而非访问时的实时时间"""
        import src.resource
        from src.resource import LogFileResource

        class _EarlierDatetime(datetime):
            @classmethod
            def now(cls, tz=None) -> datetime:
                return datetime(2026, 2, 3, 4, 5, 6)

        class _LaterDatetime(datetime):
            @classmethod
            def now(cls, tz=None) -> datetime:
                return datetime(2026, 2, 3, 4, 5, 59)

        monkeypatch.setattr(src.resource, 'datetime', _EarlierDatetime)
        resource = LogFileResource()
        monkeypatch.setattr(src.resource, 'datetime', _LaterDatetime)

        assert '20260203-040506-ERROR.log' in resource.error.name


class TestDunderMethods:
    """__call__/__repr__/__str__ 测试"""

    def test_call_joins_paths_and_returns_new_instance(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path)
        sub = resource('a', 'b.txt')
        assert isinstance(sub, AnyResource)
        assert sub is not resource
        assert sub.path == tmp_path / 'a' / 'b.txt'
        assert resource.path == tmp_path

    def test_repr(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'f.txt')
        assert repr(resource) == f'AnyResource(path={resource.resolve_path!r})'

    def test_str(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'f.txt')
        assert str(resource) == resource.resolve_path


_MAX_NAME_LENGTH = 255
_ASCII_SAFE_CHARS = frozenset(string.ascii_letters + string.digits + '-_%.~')
_WINDOWS_RESERVED_NAMES = frozenset(
    ['CON', 'PRN', 'AUX', 'NUL'] + [f'COM{i}' for i in range(1, 10)] + [f'LPT{i}' for i in range(1, 10)]
)
_CLEANER_NAMES = ['clean_ascii_valid_filename', 'clean_ascii_valid_dirname']


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8', errors='namereplace')).hexdigest()


def _short_hash(value: str) -> str:
    return _sha256_hex(value)[:8]


def _assert_ascii_valid_name(name: str) -> None:
    """断言清洗结果符合公开的文件名契约"""
    assert name
    assert name.isascii()
    assert set(name) <= _ASCII_SAFE_CHARS
    assert name.upper().split('.')[0] not in _WINDOWS_RESERVED_NAMES
    assert not name.endswith('.')
    assert len(name) <= _MAX_NAME_LENGTH
    assert Path(name).parts == (name,)


class TestCleanAsciiValidFilename:
    """clean_ascii_valid_filename 文件名清洗测试"""

    @pytest.mark.parametrize('name', ['foo.txt', 'archive.tar.gz', '.hidden', '100%.txt', 'a' * 255])
    def test_valid_name_returned_unchanged(self, name: str):
        from src.resource import clean_ascii_valid_filename

        assert clean_ascii_valid_filename(name) == name

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('a中b.txt', 'a%4E2Db.' + _short_hash('a中b.txt') + '.txt'),
            ('foo?.png', 'foo%3F.' + _short_hash('foo?.png') + '.png'),
            ('a/b', 'a%2Fb.' + _short_hash('a/b')),
            ('foo ', 'foo.' + _short_hash('foo ')),
            ('a\x01b', 'a%01b.' + _short_hash('a\x01b')),
            ('\U0001F600.txt', '%1F600.' + _short_hash('\U0001F600.txt') + '.txt'),
            ('CON', '%43ON.' + _short_hash('CON')),
            ('con.txt', '%63on.' + _short_hash('con.txt') + '.txt'),
            ('COM1', '%43OM1.' + _short_hash('COM1')),
        ],
    )
    def test_changed_name_gets_encoded_with_hash_suffix(self, name: str, expected: str):
        """编码非安全字符并中和保留名, 变更时按原始值追加短哈希"""
        from src.resource import clean_ascii_valid_filename

        assert clean_ascii_valid_filename(name) == expected

    @pytest.mark.parametrize(
        'name',
        [
            'foo.txt', 'a中b.txt', 'CON', 'foo ', 'a/b', 'a\\b', '../..', '../etc', '', '...', 'a\x01b',
            'a' * 256, 'a' * 300, '中' * 200, 'x?.' + 'b' * 16, '\U0001F600.txt', '\udcff',
        ],
    )
    def test_idempotent_and_always_valid(self, name: str):
        from src.resource import clean_ascii_valid_filename

        result = clean_ascii_valid_filename(name)
        assert clean_ascii_valid_filename(result) == result
        _assert_ascii_valid_name(result)

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('a' * 256, 'a' * 246 + '.' + _short_hash('a' * 256)),
            ('a' * 300, 'a' * 246 + '.' + _short_hash('a' * 300)),
            ('a' * 300 + '.png', 'a' * 242 + '.' + _short_hash('a' * 300 + '.png') + '.png'),
            ('中' * 200, ('%4E2D' * 200)[:246] + '.' + _short_hash('中' * 200)),
            ('x?.' + 'b' * 15, 'x%3F.' + _short_hash('x?.' + 'b' * 15) + '.' + 'b' * 15),
            ('x?.' + 'b' * 16, 'x%3F.' + _short_hash('x?.' + 'b' * 16) + '.bbbbbb~' + _short_hash('.' + 'b' * 16)),
        ],
    )
    def test_truncation_boundaries(self, name: str, expected: str):
        """覆盖长度 256、编码膨胀和扩展名 16/17 字节边界"""
        from src.resource import clean_ascii_valid_filename

        result = clean_ascii_valid_filename(name)
        assert result == expected
        _assert_ascii_valid_name(result)

    def test_custom_max_length(self):
        from src.resource import clean_ascii_valid_filename

        name = 'a' * 300
        result = clean_ascii_valid_filename(name, max_length=192)

        assert result == 'a' * 183 + '.' + _short_hash(name)
        assert len(result) == 192
        assert clean_ascii_valid_filename(result) == result
        assert clean_ascii_valid_filename(result, max_length=192) == result

    def test_custom_max_length_allows_full_hash_fallback(self):
        from src.resource import clean_ascii_valid_filename

        result = clean_ascii_valid_filename('...', max_length=64)

        assert result == _sha256_hex('...')
        assert len(result) == 64

    @pytest.mark.parametrize('max_length', [63, 256, None])
    def test_invalid_max_length_raises(self, max_length: object):
        from src.resource import clean_ascii_valid_filename

        with pytest.raises(ValueError, match='max_length'):
            clean_ascii_valid_filename('foo', max_length=max_length)


class TestCleanAsciiValidDirname:
    """clean_ascii_valid_dirname 目录名清洗测试"""

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('dir', 'dir'), ('a_b', 'a_b'), ('a.b', 'a.b'), ('100%', '100%'),
            ('a/b', 'a%2Fb'), ('a\\b', 'a%5Cb'), ('a中b', 'a%4E2Db'),
            ('foo ', 'foo'), ('foo.', 'foo'), ('a\x01b', 'a%01b'), ('\U0001F600', '%1F600'),
            ('CON', '%43ON'), ('con', '%63on'), ('CON.txt', '%43ON.txt'), ('COM1', '%43OM1'),
        ],
    )
    def test_exact_mapping(self, name: str, expected: str):
        """合法名原样返回, 非安全字符编码、首尾剥离和保留名中和不追加哈希"""
        from src.resource import clean_ascii_valid_dirname

        assert clean_ascii_valid_dirname(name) == expected

    @pytest.mark.parametrize(
        ('name', 'expected'),
        [
            ('a' * 255, 'a' * 255),
            ('a' * 256, _sha256_hex('a' * 256)),
            ('中' * 51, '%4E2D' * 51),
            ('中' * 52, _sha256_hex('中' * 52)),
            ('a' * 300, _sha256_hex('a' * 300)),
        ],
    )
    def test_encoded_length_boundary(self, name: str, expected: str):
        from src.resource import clean_ascii_valid_dirname

        result = clean_ascii_valid_dirname(name)
        assert result == expected
        _assert_ascii_valid_name(result)

    @pytest.mark.parametrize(
        'name',
        [
            'dir', 'a/b', 'a%2Fb', 'CON', 'CON.txt', '..', '../..', '../etc', ' foo', 'a\x01b',
            '\U0001F600', '\udcff', '中' * 51, '中' * 52, 'a' * 256, '',
        ],
    )
    def test_idempotent_and_always_valid(self, name: str):
        from src.resource import clean_ascii_valid_dirname

        result = clean_ascii_valid_dirname(name)
        assert clean_ascii_valid_dirname(result) == result
        _assert_ascii_valid_name(result)


class TestCleanerSharedContract:
    """两个清洗函数的共同契约与语义差异"""

    @pytest.mark.parametrize('cleaner_name', _CLEANER_NAMES)
    @pytest.mark.parametrize('name', ['', '   ', '...', '..'])
    def test_no_usable_content_falls_back_to_full_sha256(self, cleaner_name: str, name: str):
        import src.resource

        assert getattr(src.resource, cleaner_name)(name) == _sha256_hex(name)

    @pytest.mark.parametrize('cleaner_name', _CLEANER_NAMES)
    @pytest.mark.parametrize('name', [None, 123, 1.5, b'bytes'])
    def test_non_str_input_raises(self, cleaner_name: str, name: object):
        import src.resource

        with pytest.raises(ValueError, match='必须为 str 类型'):
            getattr(src.resource, cleaner_name)(name)

    @pytest.mark.parametrize('cleaner_name', _CLEANER_NAMES)
    @pytest.mark.parametrize('name', ['COM0', 'COM10', 'LPT0', 'CONSOLE'])
    def test_device_like_non_reserved_names_returned_unchanged(self, cleaner_name: str, name: str):
        import src.resource

        assert getattr(src.resource, cleaner_name)(name) == name

    def test_leading_whitespace_kept_by_filename_only(self):
        import src.resource

        assert src.resource.clean_ascii_valid_dirname(' foo') == 'foo'
        assert src.resource.clean_ascii_valid_filename(' foo') == '%20foo.' + _short_hash(' foo')

    def test_hash_suffix_only_for_filename(self):
        import src.resource

        dirname = src.resource.clean_ascii_valid_dirname
        assert dirname('a/b') == dirname('a%2Fb') == 'a%2Fb'
        assert src.resource.clean_ascii_valid_filename('a/b') != src.resource.clean_ascii_valid_filename('a%2Fb')


class TestWithMethods:
    """with_* 路径变换方法测试(均为不可变语义, 返回新实例)"""

    def test_with_name_returns_new_instance(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'old.txt')
        new_resource = resource.with_name('new.txt')
        assert new_resource is not resource
        assert isinstance(new_resource, AnyResource)
        assert new_resource.path == tmp_path / 'new.txt'
        assert resource.path == tmp_path / 'old.txt'

    def test_with_stem(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path / 'library.tar.gz').with_stem('lib').path == tmp_path / 'lib.gz'

    def test_with_suffix(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path / 'library.tar.gz').with_suffix('.bz2').path == tmp_path / 'library.tar.bz2'

    def test_with_suffix_empty_removes_suffix(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path / 'f.txt').with_suffix('').path == tmp_path / 'f'

    def test_with_suffix_without_dot_raises(self, tmp_path: Path):
        from src.resource import AnyResource

        with pytest.raises(ValueError, match='Invalid suffix'):
            AnyResource(tmp_path / 'f.txt').with_suffix('txt')

    def test_with_name_on_empty_name_raises(self):
        from src.resource import AnyResource

        with pytest.raises(ValueError, match='empty name'):
            AnyResource('').with_name('x')

    def test_with_stem_on_empty_name_raises(self):
        from src.resource import AnyResource

        with pytest.raises(ValueError, match='empty name'):
            AnyResource('').with_stem('x')

    def test_with_month_subdir_returns_new_instance(self, tmp_path: Path, fixed_datetime: datetime):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path)
        new_resource = resource.with_month_subdir_for_dir()
        assert new_resource is not resource
        assert isinstance(new_resource, AnyResource)
        assert new_resource.path == tmp_path.joinpath(fixed_datetime.strftime('%Y-%m'))
        assert resource.path == tmp_path

    def test_with_date_subdir_returns_new_instance(self, tmp_path: Path, fixed_datetime: datetime):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path)
        new_resource = resource.with_date_subdir_for_dir()
        assert new_resource is not resource
        assert isinstance(new_resource, AnyResource)
        assert new_resource.path == tmp_path.joinpath(*fixed_datetime.strftime('%Y-%m-%d').split('-'))
        assert resource.path == tmp_path

    def test_with_suffix_subdir_for_file(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'foo.pdf')
        new_resource = resource.with_suffix_subdir_for_file()
        assert new_resource is not resource
        assert isinstance(new_resource, AnyResource)
        assert new_resource.path == tmp_path / 'pdf' / 'foo.pdf'
        assert resource.path == tmp_path / 'foo.pdf'

    def test_with_suffix_subdir_without_suffix_is_noop(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'foo')
        new_resource = resource.with_suffix_subdir_for_file()
        assert new_resource is not resource
        assert new_resource.path == tmp_path / 'foo'
        assert resource.path == tmp_path / 'foo'


class TestPathProperties:
    """路径属性测试"""

    def test_name_suffix_stem(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'library.tar.gz')
        assert resource.name == 'library.tar.gz'
        assert resource.suffix == '.gz'
        assert resource.stem == 'library.tar'

    def test_no_extension(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'library')
        assert resource.name == 'library'
        assert resource.suffix == ''
        assert resource.stem == 'library'

    def test_existence_properties_on_file(self, sample_file: _SampleFileFactory):
        from src.resource import AnyResource

        file = sample_file('f.txt', 'x')
        resource = AnyResource(file)
        assert resource.is_exist
        assert resource.is_file
        assert not resource.is_dir

    def test_existence_properties_on_dir(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path)
        assert resource.is_exist
        assert not resource.is_file
        assert resource.is_dir

    def test_existence_properties_on_missing(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'missing')
        assert not resource.is_exist
        assert not resource.is_file
        assert not resource.is_dir

    def test_resolve_path(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'f.txt')
        assert resource.resolve_path == (tmp_path / 'f.txt').resolve().as_posix()
        assert Path(resource.resolve_path).is_absolute()

    def test_parent_property(self, tmp_path: Path, sample_file: _SampleFileFactory):
        from src.resource import AnyResource

        file = sample_file('f.txt', 'x')
        parent = AnyResource(file).parent
        assert isinstance(parent, AnyResource)
        assert parent.path == tmp_path.absolute()

    def test_parent_property_has_no_disk_side_effect(self, tmp_path: Path):
        """parent 属性为纯路径计算, 不在磁盘上创建目录"""
        from src.resource import AnyResource

        parent = AnyResource(tmp_path / 'deep' / 'deeper' / 'f.txt').parent
        assert parent.path == (tmp_path / 'deep' / 'deeper').absolute()
        assert not tmp_path.joinpath('deep').exists()

    def test_ensure_parent_path_creates_missing_parent(self, tmp_path: Path):
        from src.resource import AnyResource

        AnyResource(tmp_path / 'deep' / 'f.txt').ensure_parent_path()
        assert tmp_path.joinpath('deep').is_dir()

    def test_ensure_parent_path_with_existing_parent(self, tmp_path: Path):
        from src.resource import AnyResource

        AnyResource(tmp_path / 'f.txt').ensure_parent_path()
        assert tmp_path.is_dir()


class TestRaiseHelpers:
    """raise_not_file/raise_not_dir 测试"""

    @pytest.mark.parametrize(
        ('method', 'target', 'exc_class_name'),
        [
            ('raise_not_file', 'file', None),
            ('raise_not_file', 'dir', 'ResourceNotFileError'),
            ('raise_not_file', 'missing', 'ResourceNotFileError'),
            ('raise_not_dir', 'dir', None),
            ('raise_not_dir', 'file', 'ResourceNotFolderError'),
            ('raise_not_dir', 'missing', 'ResourceNotFolderError'),
        ],
        ids=[
            'not_file_on_file_passes',
            'not_file_on_dir_raises',
            'not_file_on_missing_raises',
            'not_dir_on_dir_passes',
            'not_dir_on_file_raises',
            'not_dir_on_missing_raises',
        ],
    )
    def test_raise_not_file_or_dir(
            self,
            tmp_path: Path,
            sample_file: _SampleFileFactory,
            method: str,
            target: str,
            exc_class_name: str | None,
    ):
        import src.resource
        from src.resource import AnyResource

        match target:
            case 'file':
                resource = AnyResource(sample_file('f.txt', 'x'))
            case 'dir':
                resource = AnyResource(tmp_path)
            case _:
                resource = AnyResource(tmp_path / 'missing')

        if exc_class_name is None:
            assert getattr(resource, method)() is None
        else:
            with pytest.raises(getattr(src.resource, exc_class_name)) as exc_info:
                getattr(resource, method)()
            assert exc_info.value.path == resource.path


class TestOpenSync:
    """同步 open 测试"""

    def test_write_read_text_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.txt')
        with resource.open('w', encoding='utf-8') as f:
            f.write(_SYNC_TEXT_CONTENT)
        with resource.open('r', encoding='utf-8') as f:
            assert f.read() == _SYNC_TEXT_CONTENT

    def test_write_read_binary_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.bin')
        with resource.open('wb') as f:
            f.write(_BINARY_CONTENT)
        with resource.open('rb') as f:
            assert f.read() == _BINARY_CONTENT

    def test_open_write_creates_missing_parent_dirs(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'deep' / 'nested' / 'a.txt')
        with resource.open('w', encoding='utf-8') as f:
            f.write(_NESTED_FILE_CONTENT)
        assert tmp_path.joinpath('deep', 'nested', 'a.txt').is_file()

    def test_open_with_keyword_mode(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'kw.txt')
        with resource.open(mode='w', encoding='utf-8') as f:
            f.write('kw')
        assert tmp_path.joinpath('kw.txt').read_text(encoding='utf-8') == 'kw'

    def test_open_read_missing_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        resource = AnyResource(tmp_path / 'missing.txt')
        with pytest.raises(ResourceNotFileError), resource.open('r'):
            pass

    def test_open_read_missing_creates_no_parent_dirs(self, tmp_path: Path):
        """读模式下缺失文件直接报 ResourceNotFileError, 不在磁盘上残留父目录"""
        from src.resource import AnyResource, ResourceNotFileError

        resource = AnyResource(tmp_path / 'newdir' / 'missing.txt')
        with pytest.raises(ResourceNotFileError), resource.open('r'):
            pass
        assert not tmp_path.joinpath('newdir').exists()

    def test_open_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError), AnyResource(tmp_path).open('r'):
            pass


class TestOpenAsync:
    """异步 async_open 测试"""

    async def test_async_write_read_text_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.txt')
        async with resource.async_open('w', encoding='utf-8') as af:
            await af.write(_ASYNC_TEXT_CONTENT)
        async with resource.async_open('r', encoding='utf-8') as af:
            assert await af.read() == _ASYNC_TEXT_CONTENT

    async def test_async_write_read_binary_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.bin')
        async with resource.async_open('wb') as af:
            await af.write(_BINARY_CONTENT)
        async with resource.async_open('rb') as af:
            assert await af.read() == _BINARY_CONTENT

    async def test_async_open_write_creates_missing_parent_dirs(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'deep' / 'nested' / 'a.txt')
        async with resource.async_open('w', encoding='utf-8') as af:
            await af.write(_NESTED_FILE_CONTENT)
        assert tmp_path.joinpath('deep', 'nested', 'a.txt').is_file()

    async def test_async_open_read_missing_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        # 校验发生在进入异步上下文时
        with pytest.raises(ResourceNotFileError):
            await AnyResource(tmp_path / 'missing.txt').async_open('r').__aenter__()

    async def test_async_open_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            await AnyResource(tmp_path).async_open('r').__aenter__()


class TestSafeWrite:
    """safe_write_* 安全写入方法测试(先写同目录临时文件再原子替换)"""

    async def test_safe_write_text_roundtrip(self, tmp_path: Path):
        """写入新文件内容一致, 完成后无临时文件残留"""
        from src.resource import AnyResource

        await AnyResource(tmp_path / 'a.txt').safe_write_text(_ASYNC_TEXT_CONTENT, encoding='utf-8')

        assert tmp_path.joinpath('a.txt').read_text(encoding='utf-8') == _ASYNC_TEXT_CONTENT
        assert list(tmp_path.glob('*.tmp')) == []

    async def test_safe_write_text_overwrites_existing(self, tmp_path: Path):
        """已存在文件被完整替换(长内容覆写为短内容, 抓未截断问题)"""
        from src.resource import AnyResource

        target = tmp_path / 'exist.txt'
        target.write_text('a much longer original content', encoding='utf-8')

        await AnyResource(target).safe_write_text('short', encoding='utf-8')

        assert target.read_text(encoding='utf-8') == 'short'

    async def test_safe_write_text_creates_missing_parent_dirs(self, tmp_path: Path):
        """目标父目录缺失时自动创建(与 async_open 写模式行为一致)"""
        from src.resource import AnyResource

        await AnyResource(tmp_path / 'deep' / 'nested' / 'a.txt').safe_write_text(
            _NESTED_FILE_CONTENT, encoding='utf-8',
        )

        assert tmp_path.joinpath('deep', 'nested', 'a.txt').read_text(encoding='utf-8') == _NESTED_FILE_CONTENT

    async def test_safe_write_text_honors_encoding(self, tmp_path: Path):
        """显式 encoding 透传到写入, 非 ASCII 内容按指定编码落盘"""
        from src.resource import AnyResource

        target = tmp_path / 'zh.txt'
        await AnyResource(target).safe_write_text('测试内容', encoding='utf-8')

        assert target.read_bytes() == '测试内容'.encode()

    async def test_safe_write_text_lines_roundtrip(self, tmp_path: Path):
        """多行写入不自动补换行(writelines 语义), 完成后无临时文件残留"""
        from src.resource import AnyResource

        target = tmp_path / 'lines.txt'
        await AnyResource(target).safe_write_text_lines(['line1\n', 'line2\n'], encoding='utf-8')

        assert target.read_text(encoding='utf-8') == 'line1\nline2\n'
        assert list(tmp_path.glob('*.tmp')) == []

    async def test_safe_write_text_lines_accepts_generator(self, tmp_path: Path):
        """lines 参数契约为 Iterable, 生成器入参可正常写入"""
        from src.resource import AnyResource

        target = tmp_path / 'gen.txt'
        await AnyResource(target).safe_write_text_lines((f'{i}\n' for i in range(3)), encoding='utf-8')

        assert target.read_text(encoding='utf-8') == '0\n1\n2\n'

    async def test_safe_write_text_lines_failure_preserves_original(self, tmp_path: Path):
        """写入中途失败时异常向外传播, 原文件内容保持完整"""
        from src.resource import AnyResource

        target = tmp_path / 'f.txt'
        target.write_text('original', encoding='utf-8')

        def _broken_lines():
            yield 'partial\n'
            raise RuntimeError('write interrupted')

        with pytest.raises(RuntimeError, match='write interrupted'):
            await AnyResource(target).safe_write_text_lines(_broken_lines(), encoding='utf-8')

        assert target.read_text(encoding='utf-8') == 'original'

    async def test_safe_write_text_lines_failure_leaves_no_tmp_file(self, tmp_path: Path):
        """写入中途失败后清理临时文件, 不残留 .tmp 垃圾"""
        from src.resource import AnyResource

        def _broken_lines():
            yield 'partial\n'
            raise RuntimeError('write interrupted')

        with pytest.raises(RuntimeError, match='write interrupted'):
            await AnyResource(tmp_path / 'f.txt').safe_write_text_lines(_broken_lines(), encoding='utf-8')

        assert list(tmp_path.glob('*.tmp')) == []

    async def test_safe_write_bytes_roundtrip(self, tmp_path: Path):
        """二进制内容写入并覆盖已有文件, 完成后无临时文件残留"""
        from src.resource import AnyResource

        target = tmp_path / 'a.bin'
        target.write_bytes(b'old content longer')

        await AnyResource(target).safe_write_bytes(_BINARY_CONTENT)

        assert target.read_bytes() == _BINARY_CONTENT
        assert list(tmp_path.glob('*.tmp')) == []

    @pytest.mark.parametrize('content_type', [bytearray, memoryview], ids=['bytearray', 'memoryview'])
    async def test_safe_write_bytes_accepts_buffer_like_content(
            self, tmp_path: Path, content_type: 'type[bytearray | memoryview]',
    ):
        """写入内容契约为 Buffer, bytes 之外的 buffer 类型(bytearray/memoryview)同样可写"""
        from src.resource import AnyResource

        target = tmp_path / 'buf.bin'
        await AnyResource(target).safe_write_bytes(content_type(_BINARY_CONTENT))

        assert target.read_bytes() == _BINARY_CONTENT
        assert list(tmp_path.glob('*.tmp')) == []


class TestReadTextBytes:
    """read_text/read_bytes 只读读取方法测试"""

    async def test_read_text_roundtrip(self, tmp_path: Path):
        """默认编码读回写入内容一致"""
        from src.resource import AnyResource

        target = tmp_path / 'a.txt'
        target.write_text(_ASYNC_TEXT_CONTENT, encoding='utf-8')

        assert await AnyResource(target).read_text() == _ASYNC_TEXT_CONTENT

    async def test_read_text_honors_encoding(self, tmp_path: Path):
        """显式 encoding 透传到读取, 非 ASCII 内容按指定编码解析"""
        from src.resource import AnyResource

        target = tmp_path / 'zh.txt'
        target.write_bytes('测试内容'.encode())

        assert await AnyResource(target).read_text(encoding='utf-8') == '测试内容'

    async def test_read_text_kwargs_errors_passthrough(self, tmp_path: Path):
        """**kwargs 透传到底层打开调用(errors='replace' 容错读取非法字节)"""
        from src.resource import AnyResource

        target = tmp_path / 'bad.txt'
        target.write_bytes(b'ok \xff\xfe')

        assert await AnyResource(target).read_text(encoding='utf-8', errors='replace') == 'ok \ufffd\ufffd'

    @pytest.mark.parametrize('method', ['read_text', 'read_bytes'])
    @pytest.mark.parametrize('target', ['missing', 'directory'], ids=['missing_raises', 'on_directory_raises'])
    async def test_read_on_missing_or_directory_raises(self, tmp_path: Path, method: str, target: str):
        """缺失文件或目录目标抛 ResourceNotFileError(校验在 async_open 读模式入口处)"""
        from src.resource import AnyResource, ResourceNotFileError

        resource = AnyResource(tmp_path / 'missing.txt') if target == 'missing' else AnyResource(tmp_path)
        with pytest.raises(ResourceNotFileError):
            await getattr(resource, method)()

    async def test_read_bytes_roundtrip(self, tmp_path: Path):
        """二进制内容读回一致"""
        from src.resource import AnyResource

        target = tmp_path / 'a.bin'
        target.write_bytes(_BINARY_CONTENT)

        assert await AnyResource(target).read_bytes() == _BINARY_CONTENT


class TestFileUriAndSize:
    """file_uri/file_size 属性测试"""

    def test_file_uri(self, sample_file: _SampleFileFactory):
        from src.resource import AnyResource

        file = sample_file('f.txt', 'x')
        assert AnyResource(file).file_uri.startswith('file:///')

    def test_file_size(self, sample_file: _SampleFileFactory):
        from src.resource import AnyResource

        file = sample_file('f.txt', b'12345')
        assert AnyResource(file).file_size == 5

    @pytest.mark.parametrize(
        ('attr', 'target'),
        [
            ('file_uri', 'missing'),
            ('file_uri', 'dir'),
            ('file_size', 'missing'),
            ('file_size', 'dir'),
        ],
        ids=[
            'file_uri_missing_raises',
            'file_uri_on_directory_raises',
            'file_size_missing_raises',
            'file_size_on_directory_raises',
        ],
    )
    def test_missing_or_directory_target_raises(self, tmp_path: Path, attr: str, target: str):
        from src.resource import AnyResource, ResourceNotFileError

        resource = AnyResource(tmp_path / 'missing.txt') if target == 'missing' else AnyResource(tmp_path)
        with pytest.raises(ResourceNotFileError):
            getattr(resource, attr)


class TestListFiles:
    """目录遍历方法测试"""

    def test_list_all_files_recursive(self, sample_tree: Path):
        from src.resource import AnyResource

        files = AnyResource(sample_tree).list_all_files()
        assert {f.name for f in files} == {'a.txt', 'b.txt'}
        assert all(isinstance(f, AnyResource) for f in files)

    def test_list_current_files_not_recursive(self, sample_tree: Path):
        from src.resource import AnyResource

        files = AnyResource(sample_tree).list_current_files()
        assert {f.name for f in files} == {'a.txt'}

    def test_iter_all_files_recursive(self, sample_tree: Path):
        from src.resource import AnyResource

        files = list(AnyResource(sample_tree).iter_all_files())
        assert {f.name for f in files} == {'a.txt', 'b.txt'}

    def test_iter_current_files_not_recursive(self, sample_tree: Path):
        from src.resource import AnyResource

        files = list(AnyResource(sample_tree).iter_current_files())
        assert {f.name for f in files} == {'a.txt'}

    def test_list_empty_dir(self, tmp_path: Path):
        from src.resource import AnyResource

        tmp_path.joinpath('empty').mkdir()
        assert AnyResource(tmp_path / 'empty').list_all_files() == []
        assert AnyResource(tmp_path / 'empty').list_current_files() == []

    def test_list_on_file_raises(self, sample_tree: Path):
        from src.resource import AnyResource, ResourceNotFolderError

        with pytest.raises(ResourceNotFolderError):
            AnyResource(sample_tree / 'a.txt').list_all_files()

    def test_list_on_missing_dir_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFolderError

        with pytest.raises(ResourceNotFolderError):
            AnyResource(tmp_path / 'missing').list_current_files()

    def test_iter_on_file_raises(self, sample_tree: Path):
        from src.resource import AnyResource, ResourceNotFolderError

        with pytest.raises(ResourceNotFolderError):
            AnyResource(sample_tree / 'a.txt').iter_all_files()


class TestRenameReplaceRemove:
    """rename/replace/remove 测试"""

    def test_rename(self, tmp_path: Path):
        from src.resource import AnyResource

        tmp_path.joinpath('old.txt').write_text('x', encoding='utf-8')
        new_resource = AnyResource(tmp_path / 'old.txt').rename(tmp_path / 'new.txt')
        assert isinstance(new_resource, AnyResource)
        assert new_resource.path == tmp_path / 'new.txt'
        assert not tmp_path.joinpath('old.txt').exists()
        assert tmp_path.joinpath('new.txt').is_file()

    @pytest.mark.parametrize('method', ['rename', 'replace'])
    @pytest.mark.parametrize('source', ['missing', 'directory'])
    def test_missing_or_directory_source_raises(self, tmp_path: Path, method: str, source: str):
        from src.resource import AnyResource, ResourceNotFileError

        resource = AnyResource(tmp_path / 'missing.txt') if source == 'missing' else AnyResource(tmp_path)
        with pytest.raises(ResourceNotFileError):
            getattr(resource, method)(tmp_path / 'new')

    def test_replace_overwrites_existing_target(self, tmp_path: Path):
        from src.resource import AnyResource

        tmp_path.joinpath('old.txt').write_text('new content', encoding='utf-8')
        tmp_path.joinpath('exist.txt').write_text('old content', encoding='utf-8')
        AnyResource(tmp_path / 'old.txt').replace(tmp_path / 'exist.txt')
        assert not tmp_path.joinpath('old.txt').exists()
        assert tmp_path.joinpath('exist.txt').read_text(encoding='utf-8') == 'new content'

    def test_remove_existing_file(self, sample_file: _SampleFileFactory):
        from src.resource import AnyResource

        file = sample_file('f.txt', 'x')
        AnyResource(file).remove()
        assert not file.exists()

    def test_remove_missing_file_default_missing_ok(self, tmp_path: Path):
        """缺失文件默认静默, 且不创建任何父目录"""
        from src.resource import AnyResource

        AnyResource(tmp_path / 'newdir' / 'missing.txt').remove()
        assert not tmp_path.joinpath('newdir').exists()

    def test_remove_missing_file_not_missing_ok_raises(self, tmp_path: Path):
        from src.resource import AnyResource

        with pytest.raises(FileNotFoundError):
            AnyResource(tmp_path / 'missing.txt').remove(missing_ok=False)

    def test_remove_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path).remove()


class TestHostProtocol:
    """文件托管协议测试(使用继承 BaseResource 的本地子类隔离注册状态, 不污染全局类)"""

    @staticmethod
    def _make_hostable_resource():
        from src.resource import BaseResource, BaseResourceHostProtocol

        class _FakeProtocol(BaseResourceHostProtocol):
            async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> tuple[str, str]:
                return 'url', f'https://fake.host/{self._resource.name}?ttl={ttl_delta}'

        class _HostableResource(BaseResource):
            """隔离测试用资源类: 直接继承 BaseResource, 不受 omega_file_host 全局注册状态影响"""

            def __init__(self, path: str | Path) -> None:
                self.path = Path(path)

        return _HostableResource, _FakeProtocol

    async def test_unregistered_class_returns_resolve_path(self, sample_file: _SampleFileFactory):
        """未注册协议的类, get_hosting_path 回退为本地路径"""
        hostable_resource, _ = self._make_hostable_resource()

        file = sample_file('f.txt', 'x')
        assert await hostable_resource(file).get_hosting_path() == ('path', hostable_resource(file).resolve_path)

    async def test_registered_protocol_returns_url(self, sample_file: _SampleFileFactory):
        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)

        file = sample_file('f.txt', 'x')
        assert await hostable_resource(file).get_hosting_path(ttl_delta=60) == ('url', 'https://fake.host/f.txt?ttl=60')

    def test_register_twice_raises(self):
        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)
        with pytest.raises(RuntimeError):
            hostable_resource.register_host_protocol(protocol)

    def test_register_invalid_protocol_raises(self):
        hostable_resource, _ = self._make_hostable_resource()
        with pytest.raises(TypeError):
            hostable_resource.register_host_protocol(object)

    def test_register_on_subclass_does_not_pollute_base(self):
        """子类注册协议不影响基类及其他类的注册状态"""
        from src.resource import AnyResource, BaseResource

        before_any = AnyResource._host_protocol  # 快照, 与 omega_file_host 是否已导入无关

        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)

        assert hostable_resource._host_protocol is protocol
        assert BaseResource._host_protocol is None
        assert AnyResource._host_protocol is before_any

    async def test_unregister_restores_resolve_path_fallback(self, sample_file: _SampleFileFactory):
        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)

        file = sample_file('f.txt', 'x')
        assert await hostable_resource(file).get_hosting_path() == ('url', 'https://fake.host/f.txt?ttl=0')

        hostable_resource.unregister_host_protocol()
        assert await hostable_resource(file).get_hosting_path() == ('path', hostable_resource(file).resolve_path)

    def test_unregister_without_registration_is_noop(self):
        hostable_resource, _ = self._make_hostable_resource()
        hostable_resource.unregister_host_protocol()
        assert hostable_resource._host_protocol is None

    async def test_protocol_base_method_raises_not_implemented(self):
        from src.resource import AnyResource, BaseResourceHostProtocol

        class _Protocol(BaseResourceHostProtocol):
            async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> tuple[str, str]:
                return await super().get_hosting_file_path(ttl_delta=ttl_delta)

        with pytest.raises(NotImplementedError):
            await _Protocol(AnyResource('.')).get_hosting_file_path()


class TestGlobalHostProtocolRegistration:
    """omega_file_host 全局注册契约测试 (本地资源统一注册 OmegaFileHostProtocol)"""

    def test_registered_class_rejects_second_registration(self):
        """已全局注册的类拒绝再次注册, 异常先于赋值抛出, 状态不被修改"""
        import src.service.omega_file_host  # noqa: F401
        from src.resource import AnyResource
        from src.service.omega_file_host import OmegaFileHostProtocol

        with pytest.raises(RuntimeError, match='already registered'):
            AnyResource.register_host_protocol(OmegaFileHostProtocol)

        assert AnyResource._host_protocol is OmegaFileHostProtocol

    def test_subclass_inherits_global_registration(self):
        """子类沿 MRO 继承全局注册的协议, 且不可覆写注册"""
        import src.service.omega_file_host  # noqa: F401
        from src.resource import AnyResource
        from src.service.omega_file_host import OmegaFileHostProtocol

        class _SubResource(AnyResource):
            pass

        assert _SubResource._host_protocol is OmegaFileHostProtocol
        with pytest.raises(RuntimeError, match='already registered'):
            _SubResource.register_host_protocol(OmegaFileHostProtocol)

    async def test_hosting_disabled_falls_back_to_resolve_path(
            self, monkeypatch: pytest.MonkeyPatch, sample_file: _SampleFileFactory,
    ):
        """托管服务配置禁用时, 已注册协议的 get_hosting_path 回退为本地路径 (不发起 HTTP 请求)"""
        from src.resource import AnyResource
        from src.service.omega_file_host.config import file_host_config

        monkeypatch.setattr(file_host_config, 'omega_file_host_enable_hosting_service', False)

        file = sample_file('f.txt', 'x')
        resource = AnyResource(file)
        assert await resource.get_hosting_path() == ('path', resource.resolve_path)

    async def test_file_check_precedes_protocol_call(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """即使启用托管服务, 缺失文件仍在 @check_file 处抛出 ResourceNotFileError, 不会发出托管请求"""
        from src.resource import AnyResource, ResourceNotFileError
        from src.service.omega_file_host.config import file_host_config

        monkeypatch.setattr(file_host_config, 'omega_file_host_enable_hosting_service', True)

        with pytest.raises(ResourceNotFileError):
            await AnyResource(tmp_path / 'missing.txt').get_hosting_path()


class TestInitFromPath:
    """_init_from_path 测试"""

    def test_init_from_path_absolute(self):
        from src.resource import AnyResource

        resource = AnyResource._init_from_path(Path('some_relative/file.txt'))
        assert resource.path.is_absolute()
        assert resource.path == Path('some_relative/file.txt').absolute()

    def test_init_from_path_preserves_class(self, tmp_path: Path):
        from src.resource import StaticResource

        resource = StaticResource._init_from_path(tmp_path / 'f.txt')
        assert isinstance(resource, StaticResource)
        assert resource.path == (tmp_path / 'f.txt').absolute()


class TestPathConfinement:
    """路径穿越防护(confinement)测试"""

    def test_out_of_root_error_contract(self, tmp_path: Path):
        from src.exception import LocalSourceException, OmegaException
        from src.resource import ResourcePathOutOfRootError

        exc = ResourcePathOutOfRootError(tmp_path / 'escape.txt', tmp_path)
        assert isinstance(exc, LocalSourceException)
        assert isinstance(exc, OmegaException)
        assert exc.path == tmp_path / 'escape.txt'
        assert exc.root == tmp_path
        assert exc.path.as_posix() in exc.message
        assert exc.root.as_posix() in exc.message
        assert 'outside of the resource root' in exc.message
        assert 'ResourcePathOutOfRootError' in repr(exc)
        assert str(exc) == repr(exc)

    def test_static_resource_parent_escape_raises(self):
        from src.resource import ResourcePathOutOfRootError, StaticResource

        with pytest.raises(ResourcePathOutOfRootError):
            StaticResource('..')
        with pytest.raises(ResourcePathOutOfRootError):
            StaticResource('fonts', '..', '..')

    def test_temporary_resource_parent_escape_raises(self):
        from src.resource import ResourcePathOutOfRootError, TemporaryResource

        with pytest.raises(ResourcePathOutOfRootError):
            TemporaryResource('..', '..', 'etc')

    def test_absolute_path_arg_raises(self, tmp_path: Path):
        """绝对路径参数会整体替换 base 根目录, 必须拦截"""
        from src.resource import ResourcePathOutOfRootError, StaticResource, TemporaryResource

        with pytest.raises(ResourcePathOutOfRootError):
            StaticResource(str(tmp_path))
        with pytest.raises(ResourcePathOutOfRootError):
            TemporaryResource(str(tmp_path))

    def test_normal_args_not_affected(self):
        import src.resource
        from src.resource import StaticResource

        static_resource = StaticResource('fonts', 'a.ttf')
        assert static_resource.path == src.resource._STATIC_RESOURCE_FOLDER.joinpath('fonts', 'a.ttf')

    def test_dotdot_staying_inside_root_allowed(self):
        """'..' 拼接但最终落在根内时放行, 且保持原始(未归一化)路径语义"""
        import src.resource
        from src.resource import StaticResource

        resource = StaticResource('fonts', '..', 'docs', 'x.txt')
        assert resource.path == src.resource._STATIC_RESOURCE_FOLDER.joinpath('fonts', '..', 'docs', 'x.txt')
        expected = src.resource._STATIC_RESOURCE_FOLDER.joinpath('docs', 'x.txt').resolve().as_posix()
        assert resource.resolve_path == expected

    def test_call_parent_escape_raises(self):
        from src.resource import ResourcePathOutOfRootError, TemporaryResource

        with pytest.raises(ResourcePathOutOfRootError):
            TemporaryResource('sub')('..', '..')

    def test_call_within_root_allowed(self):
        import src.resource
        from src.resource import TemporaryResource

        resource = TemporaryResource('sub')('nested', 'f.txt')
        assert resource.path == src.resource._TEMPORARY_RESOURCE_FOLDER.joinpath('sub', 'nested', 'f.txt')

    def test_log_resource_call_escape_raises(self):
        from src.resource import LogFileResource, ResourcePathOutOfRootError

        with pytest.raises(ResourcePathOutOfRootError):
            LogFileResource()('..', '..')

    def test_any_resource_not_confined(self, tmp_path: Path):
        """AnyResource 设计意图为任意位置资源, 不做 confinement 限制"""
        from src.resource import AnyResource

        assert AnyResource(tmp_path, '..').path == tmp_path / '..'
        assert AnyResource(tmp_path)('..').path == tmp_path / '..'
