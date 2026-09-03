"""
@Author         : Ailitonia
@Date           : 2026/9/3 19:52
@FileName       : test_002_resource
@Project        : omega-miya
@Description    : src.resource 模块单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from pathlib import Path

import pytest


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


class TestExceptions:
    """资源异常类测试"""

    def test_not_file_error(self, tmp_path: Path):
        from src.exception import LocalSourceException, OmegaException
        from src.resource import ResourceNotFileError

        exc = ResourceNotFileError(tmp_path / 'f.txt')
        assert isinstance(exc, LocalSourceException)
        assert isinstance(exc, OmegaException)
        assert exc.path == tmp_path / 'f.txt'
        assert exc.path.as_posix() in exc.message
        assert 'is not a file' in exc.message
        assert 'ResourceNotFileError' in repr(exc)
        assert str(exc) == repr(exc)

    def test_not_folder_error(self, tmp_path: Path):
        from src.exception import LocalSourceException, OmegaException
        from src.resource import ResourceNotFolderError

        exc = ResourceNotFolderError(tmp_path / 'd')
        assert isinstance(exc, LocalSourceException)
        assert isinstance(exc, OmegaException)
        assert exc.path == tmp_path / 'd'
        assert exc.path.as_posix() in exc.message
        assert 'is not a directory' in exc.message
        assert 'ResourceNotFolderError' in repr(exc)
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
            'LogFileResource',
            'StaticResource',
            'TemporaryResource',
            'ResourceNotFolderError',
            'ResourceNotFileError',
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

    def test_debug(self, fixed_datetime: datetime):
        import src.resource
        from src.resource import LogFileResource

        path = LogFileResource().debug
        assert isinstance(path, Path)
        assert path == src.resource._LOG_FOLDER.joinpath('2026-02', '20260203-040506-DEBUG.log')

    def test_info(self, fixed_datetime: datetime):
        import src.resource
        from src.resource import LogFileResource

        assert LogFileResource().info == src.resource._LOG_FOLDER.joinpath('2026-02', '20260203-040506-INFO.log')

    def test_warning(self, fixed_datetime: datetime):
        import src.resource
        from src.resource import LogFileResource

        assert LogFileResource().warning == src.resource._LOG_FOLDER.joinpath('2026-02', '20260203-040506-WARNING.log')

    def test_error(self, fixed_datetime: datetime):
        import src.resource
        from src.resource import LogFileResource

        path = LogFileResource().error
        assert isinstance(path, Path)
        assert path == src.resource._LOG_FOLDER.joinpath('2026-02', '20260203-040506-ERROR.log')

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

    def test_existence_properties_on_file(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
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

    def test_parent_property(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
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

    def test_raise_not_file_on_file(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        assert AnyResource(file).raise_not_file() is None

    def test_raise_not_file_on_dir(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError) as exc_info:
            AnyResource(tmp_path).raise_not_file()
        assert exc_info.value.path == tmp_path

    def test_raise_not_file_on_missing(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path / 'missing.txt').raise_not_file()

    def test_raise_not_dir_on_dir(self, tmp_path: Path):
        from src.resource import AnyResource

        assert AnyResource(tmp_path).raise_not_dir() is None

    def test_raise_not_dir_on_file(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFolderError

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        with pytest.raises(ResourceNotFolderError) as exc_info:
            AnyResource(file).raise_not_dir()
        assert exc_info.value.path == file

    def test_raise_not_dir_on_missing(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFolderError

        with pytest.raises(ResourceNotFolderError):
            AnyResource(tmp_path / 'missing').raise_not_dir()


class TestOpenSync:
    """同步 open 测试"""

    def test_write_read_text_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.txt')
        with resource.open('w', encoding='utf-8') as f:
            f.write('hello')
        with resource.open('r', encoding='utf-8') as f:
            assert f.read() == 'hello'

    def test_write_read_binary_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.bin')
        with resource.open('wb') as f:
            f.write(b'\x00\x01')
        with resource.open('rb') as f:
            assert f.read() == b'\x00\x01'

    def test_open_write_creates_missing_parent_dirs(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'deep' / 'nested' / 'a.txt')
        with resource.open('w', encoding='utf-8') as f:
            f.write('x')
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
            await af.write('async hello')
        async with resource.async_open('r', encoding='utf-8') as af:
            assert await af.read() == 'async hello'

    async def test_async_write_read_binary_roundtrip(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'a.bin')
        async with resource.async_open('wb') as af:
            await af.write(b'\x00\x01')
        async with resource.async_open('rb') as af:
            assert await af.read() == b'\x00\x01'

    async def test_async_open_write_creates_missing_parent_dirs(self, tmp_path: Path):
        from src.resource import AnyResource

        resource = AnyResource(tmp_path / 'deep' / 'nested' / 'a.txt')
        async with resource.async_open('w', encoding='utf-8') as af:
            await af.write('x')
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


class TestFileUriAndSize:
    """file_uri/file_size 属性测试"""

    def test_file_uri(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        assert AnyResource(file).file_uri.startswith('file:///')

    def test_file_uri_missing_file_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path / 'missing.txt').file_uri  # noqa: B018

    def test_file_uri_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path).file_uri  # noqa: B018

    def test_file_size(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_bytes(b'12345')
        assert AnyResource(file).file_size == 5

    def test_file_size_missing_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path / 'missing.txt').file_size  # noqa: B018

    def test_file_size_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path).file_size  # noqa: B018


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

    def test_rename_missing_source_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path / 'missing.txt').rename(tmp_path / 'new.txt')

    def test_rename_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path).rename(tmp_path / 'new')

    def test_replace_overwrites_existing_target(self, tmp_path: Path):
        from src.resource import AnyResource

        tmp_path.joinpath('old.txt').write_text('new content', encoding='utf-8')
        tmp_path.joinpath('exist.txt').write_text('old content', encoding='utf-8')
        AnyResource(tmp_path / 'old.txt').replace(tmp_path / 'exist.txt')
        assert not tmp_path.joinpath('old.txt').exists()
        assert tmp_path.joinpath('exist.txt').read_text(encoding='utf-8') == 'new content'

    def test_replace_missing_source_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path / 'missing.txt').replace(tmp_path / 'new.txt')

    def test_replace_on_directory_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            AnyResource(tmp_path).replace(tmp_path / 'new')

    def test_remove_existing_file(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
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
    """文件托管协议测试(使用本地子类隔离注册状态, 不污染全局类)"""

    @staticmethod
    def _make_hostable_resource():
        from src.resource import AnyResource, BaseResourceHostProtocol

        class _FakeProtocol(BaseResourceHostProtocol):
            async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> str:
                return f'https://fake.host/{self._resource.name}?ttl={ttl_delta}'

        class _HostableResource(AnyResource):
            pass

        return _HostableResource, _FakeProtocol

    async def test_no_protocol_returns_resolve_path(self, tmp_path: Path):
        from src.resource import AnyResource

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        assert await AnyResource(file).get_hosting_path() == AnyResource(file).resolve_path

    async def test_get_hosting_path_on_missing_file_raises(self, tmp_path: Path):
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError):
            await AnyResource(tmp_path / 'missing.txt').get_hosting_path()

    async def test_registered_protocol_returns_url(self, tmp_path: Path):
        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        assert await hostable_resource(file).get_hosting_path(ttl_delta=60) == 'https://fake.host/f.txt?ttl=60'

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
        from src.resource import AnyResource, BaseResource

        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)
        assert BaseResource._host_protocol is None
        assert AnyResource._host_protocol is None

    async def test_unregister_restores_resolve_path_fallback(self, tmp_path: Path):
        hostable_resource, protocol = self._make_hostable_resource()
        hostable_resource.register_host_protocol(protocol)

        file = tmp_path / 'f.txt'
        file.write_text('x', encoding='utf-8')
        assert await hostable_resource(file).get_hosting_path() == 'https://fake.host/f.txt?ttl=0'

        hostable_resource.unregister_host_protocol()
        assert await hostable_resource(file).get_hosting_path() == hostable_resource(file).resolve_path

    def test_unregister_without_registration_is_noop(self):
        hostable_resource, _ = self._make_hostable_resource()
        hostable_resource.unregister_host_protocol()
        assert hostable_resource._host_protocol is None

    async def test_protocol_base_method_raises_not_implemented(self):
        from src.resource import AnyResource, BaseResourceHostProtocol

        class _Protocol(BaseResourceHostProtocol):
            async def get_hosting_file_path(self, *, ttl_delta: int = 0) -> str:
                return await super().get_hosting_file_path(ttl_delta=ttl_delta)

        with pytest.raises(NotImplementedError):
            await _Protocol(AnyResource('.')).get_hosting_file_path()


class TestInitFromPath:
    """init_from_path 测试"""

    def test_init_from_path_absolute(self):
        from src.resource import AnyResource

        resource = AnyResource.init_from_path(Path('some_relative/file.txt'))
        assert resource.path.is_absolute()
        assert resource.path == Path('some_relative/file.txt').absolute()

    def test_init_from_path_preserves_class(self, tmp_path: Path):
        from src.resource import StaticResource

        resource = StaticResource.init_from_path(tmp_path / 'f.txt')
        assert isinstance(resource, StaticResource)
        assert resource.path == (tmp_path / 'f.txt').absolute()
