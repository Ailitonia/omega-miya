"""
@Author         : Ailitonia
@Date           : 2026/9/5 17:26
@FileName       : test_008_omega_file_host
@Project        : omega-miya
@Description    : omega_file_host 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.global_cache import GlobalCache

_FILE_HOST_CACHE_NAME = 'omega_file_host'
"""被测模块使用的全局缓存名称"""

_TEST_DATETIME_PAST = datetime(1990, 1, 1)
"""测试用已过期时间点"""

_ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


def _make_uuid(path_str: str) -> str:
    """按模块实现计算指定路径字符串对应的文件 UUID"""
    return uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=path_str).hex


def _make_test_file(tmp_path: Path, name: str = 'test_file.txt', content: bytes = b'test file content') -> Path:
    """在临时目录创建已知内容的测试文件"""
    file = tmp_path / name
    file.write_bytes(content)
    return file


async def _seed_row_direct(cache_key: str, cache_value: str, expired_time: datetime | timedelta | None = None) -> None:
    """经 DAL 直接写入缓存行并提交(不经过被测模块的内存缓存)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        await dal.add_update_exist(
            cache_name=_FILE_HOST_CACHE_NAME,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_time=expired_time,
        )
        await dal.commit_session()


async def _query_row_or_none(cache_key: str, *, include_expired: bool = True) -> 'GlobalCache | None':
    """以独立会话查询文件托管缓存行, 不存在返回 None"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        try:
            return await dal.query_unique(_FILE_HOST_CACHE_NAME, cache_key, include_expired=include_expired)
        except NoResultFound:
            return None


async def _query_all_keys() -> set[str]:
    """以独立会话查询文件托管缓存全部键(含已过期)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        rows = await dal.query_series(_FILE_HOST_CACHE_NAME, include_expired=True)
    return {row.cache_key for row in rows}


async def _delete_file_host_rows(cache_keys: list[str]) -> None:
    """物理删除指定的文件托管缓存行"""
    if not cache_keys:
        return

    from src.database.helpers import database_session
    from src.database.schema import GlobalCacheOrm

    async with database_session() as session:
        await session.execute(
            delete(GlobalCacheOrm)
            .where(GlobalCacheOrm.cache_name == _FILE_HOST_CACHE_NAME)
            .where(GlobalCacheOrm.cache_key.in_(cache_keys))
        )


def _get_cache_ttl() -> int:
    """获取配置的文件托管缓存时间"""
    from src.service.omega_file_host.config import file_host_config

    return file_host_config.omega_file_host_cache_ttl


@pytest.fixture
async def file_host_row_tracker() -> AsyncGenerator[list[str], None]:
    """跟踪测试产生的文件托管缓存键, 测试后定点清理数据库行(模块单例不注销)"""
    created: list[str] = []

    yield created

    await _delete_file_host_rows(created)


@pytest.fixture
async def download_client() -> AsyncGenerator[AsyncClient, None]:
    """直打文件托管子应用的 HTTP 客户端(免 token 校验)"""
    from src.service.omega_file_host import api as file_host_api

    async with AsyncClient(
            transport=ASGITransport(app=file_host_api._FILE_HOST_API._app),
            base_url='http://testserver',
    ) as client:
        yield client


class TestModuleContract:
    """模块导出与单例契约测试"""

    def test_module_importable_and_all(self) -> None:
        """模块应可正常导入(注册托管协议不应抛出 TypeError)"""
        from src.service import omega_file_host

        assert omega_file_host.__all__ == ['get_file_download_url', 'query_file_uuid', 'query_file_real_path']

    def test_exported_functions(self) -> None:
        import inspect

        from src.service import omega_file_host

        assert inspect.iscoroutinefunction(omega_file_host.query_file_uuid)
        assert inspect.iscoroutinefunction(omega_file_host.query_file_real_path)
        assert not inspect.iscoroutinefunction(omega_file_host.get_file_download_url)
        assert inspect.signature(omega_file_host.query_file_uuid).return_annotation is str
        assert inspect.signature(omega_file_host.query_file_real_path).return_annotation == str | None
        assert inspect.signature(omega_file_host.get_file_download_url).return_annotation is str

    def test_host_protocol_registered(self) -> None:
        """AnyResource/StaticResource/TemporaryResource 应已注册托管协议, LogFileResource 不注册"""
        from src.resource import (
            AnyResource,
            BaseResourceHostProtocol,
            LogFileResource,
            StaticResource,
            TemporaryResource,
        )
        from src.service.omega_file_host import OmegaFileHostProtocol

        for resource_class in (AnyResource, StaticResource, TemporaryResource):
            assert resource_class._host_protocol is OmegaFileHostProtocol
            assert issubclass(resource_class._host_protocol, BaseResourceHostProtocol)

        assert LogFileResource._host_protocol is None

    def test_singletons_contract(self) -> None:
        from src.service.omega_file_host import api as file_host_api
        from src.service.omega_file_host.config import file_host_config

        assert file_host_api._FILE_HOST_API._app_name == 'omega_file_host'
        assert file_host_api._FILE_HOST_API._enable_token_verify is False
        assert file_host_api._FILE_HOST_CACHE._cache_name == 'omega_file_host'
        assert file_host_api._FILE_HOST_CACHE._ttl == file_host_config.omega_file_host_cache_ttl

    def test_sync_job_registered(self) -> None:
        """托管服务启用时, 缓存同步定时任务应已注册"""
        from src.service.apscheduler import scheduler
        from src.service.omega_file_host.config import file_host_config

        if not file_host_config.omega_file_host_enable_hosting_service:
            pytest.skip('文件托管服务未启用')

        assert scheduler.get_job('omega_file_host_sync_file_host_cache') is not None

    def test_download_route_registered(self) -> None:
        """托管服务启用时, 下载路由应已注册到子应用"""
        from src.service.omega_file_host import api as file_host_api
        from src.service.omega_file_host.config import file_host_config

        if not file_host_config.omega_file_host_enable_hosting_service:
            pytest.skip('文件托管服务未启用')

        routes = [route for route in file_host_api._FILE_HOST_API._app.routes
                  if getattr(route, 'path', None) == '/download/{file_id}']
        assert len(routes) == 1
        assert 'GET' in routes[0].methods


class TestQueryFileUuid:
    """query_file_uuid 测试(真实数据库)"""

    async def test_returns_uuid_hex(self, tmp_path: Path, file_host_row_tracker) -> None:
        """返回值应为文件 resolve_path 对应的 uuid5 hex(32 位小写十六进制)"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(result)

        assert result == _make_uuid(resource.resolve_path)
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

    async def test_deterministic(self, tmp_path: Path, file_host_row_tracker) -> None:
        """相同文件多次调用返回相同 UUID"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        first = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(first)
        second = await omega_file_host.query_file_uuid(resource)

        assert first == second

    async def test_distinct_files_distinct_uuids(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        uuid1 = await omega_file_host.query_file_uuid(AnyResource(str(_make_test_file(tmp_path, name='f1.txt'))))
        file_host_row_tracker.append(uuid1)
        uuid2 = await omega_file_host.query_file_uuid(AnyResource(str(_make_test_file(tmp_path, name='f2.txt'))))
        file_host_row_tracker.append(uuid2)

        assert uuid1 != uuid2

    async def test_persists_row_with_default_ttl(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(result)

        row = await _query_row_or_none(result)
        assert row is not None
        assert row.cache_key == result
        assert row.cache_value == resource.resolve_path
        expected = datetime.now() + timedelta(seconds=_get_cache_ttl())
        assert abs((row.expired_at - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_ttl_delta_applied(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await omega_file_host.query_file_uuid(resource, ttl_delta=-1000)
        file_host_row_tracker.append(result)

        row = await _query_row_or_none(result)
        assert row is not None
        expected = datetime.now() + timedelta(seconds=_get_cache_ttl() - 1000)
        assert abs((row.expired_at - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_same_file_upsert_single_row(self, tmp_path: Path, file_host_row_tracker) -> None:
        """相同文件重复注册为更新而非插入"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        first = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(first)
        second = await omega_file_host.query_file_uuid(resource)

        assert first == second
        all_keys = await _query_all_keys()
        assert sum(1 for key in all_keys if key == first) == 1

    async def test_missing_file_raises(self, tmp_path: Path) -> None:
        """不存在的路径主动抛出 ValueError"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        with pytest.raises(ValueError, match='Invalid file'):
            await omega_file_host.query_file_uuid(AnyResource(str(tmp_path / 'missing.txt')))

    async def test_directory_raises(self, tmp_path: Path) -> None:
        """目录路径主动抛出 ValueError"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        with pytest.raises(ValueError, match='Invalid file'):
            await omega_file_host.query_file_uuid(AnyResource(str(tmp_path)))

    async def test_symlink_registers_target_path(self, tmp_path: Path, file_host_row_tracker) -> None:
        """符号链接经 resolve_path 解析, 实际登记其目标路径"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        target = _make_test_file(tmp_path, name='target.txt')
        link = tmp_path / 'link.txt'
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip('当前环境不支持创建符号链接')

        result = await omega_file_host.query_file_uuid(AnyResource(str(link)))
        file_host_row_tracker.append(result)

        target_resource = AnyResource(str(target))
        assert result == _make_uuid(target_resource.resolve_path)
        row = await _query_row_or_none(result)
        assert row is not None
        assert row.cache_value == target_resource.resolve_path


class TestQueryFileRealPath:
    """query_file_real_path 测试(真实数据库)"""

    async def test_load_existing(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = _make_uuid(path_str)
        await _seed_row_direct(key, path_str)
        file_host_row_tracker.append(key)

        assert await omega_file_host.query_file_real_path(key) == path_str

    async def test_load_missing_returns_none(self) -> None:
        from src.service import omega_file_host

        assert await omega_file_host.query_file_real_path(uuid.uuid4().hex) is None

    async def test_auto_refresh_extends_expiry(self, tmp_path: Path, file_host_row_tracker) -> None:
        """auto_refresh=True(默认)命中时滑动续期, expired_at 延后"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = _make_uuid(path_str)
        await _seed_row_direct(key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000))
        file_host_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        result = await omega_file_host.query_file_real_path(key)

        assert result == path_str
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_no_refresh_keeps_expiry(self, tmp_path: Path, file_host_row_tracker) -> None:
        """auto_refresh=False 命中时不续期, expired_at 不变"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = _make_uuid(path_str)
        await _seed_row_direct(key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000))
        file_host_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        result = await omega_file_host.query_file_real_path(key, auto_refresh=False)

        assert result == path_str
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert abs((row_after.expired_at - row_before.expired_at).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_expired_row_returns_none(self, tmp_path: Path, file_host_row_tracker) -> None:
        """已过期行返回 None, 且不触发续期"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = _make_uuid(path_str)
        await _seed_row_direct(key, path_str, expired_time=_TEST_DATETIME_PAST)
        file_host_row_tracker.append(key)

        assert await omega_file_host.query_file_real_path(key) is None

        row = await _query_row_or_none(key)
        assert row is not None
        assert row.expired_at == _TEST_DATETIME_PAST

    async def test_empty_uuid_raises(self) -> None:
        """空 UUID 经由全局缓存键校验抛出 ValueError"""
        from src.service import omega_file_host

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await omega_file_host.query_file_real_path('')

    async def test_refresh_missing_creates_no_row(self, file_host_row_tracker) -> None:
        """auto_refresh 对不存在的键不产生任何缓存行"""
        from src.service import omega_file_host

        key = uuid.uuid4().hex
        file_host_row_tracker.append(key)

        assert await omega_file_host.query_file_real_path(key) is None
        assert await _query_row_or_none(key) is None


class TestSyncJob:
    """_sync_file_host_cache 定时同步任务测试(真实数据库)"""

    @pytest.fixture(autouse=True)
    def _require_hosting_service(self) -> None:
        from src.service.omega_file_host.config import file_host_config

        if not file_host_config.omega_file_host_enable_hosting_service:
            pytest.skip('文件托管服务未启用')

    async def test_sync_loads_db_rows(self, file_host_row_tracker) -> None:
        """同步后内存缓存与数据库一致"""
        from src.service.omega_file_host import api as file_host_api

        key1 = uuid.uuid4().hex
        key2 = uuid.uuid4().hex
        await _seed_row_direct(key1, 'C:/path/one.txt')
        await _seed_row_direct(key2, 'C:/path/two.txt')
        file_host_row_tracker.extend([key1, key2])

        assert await file_host_api._sync_file_host_cache() is None

        assert file_host_api._FILE_HOST_CACHE._cache[key1] == 'C:/path/one.txt'
        assert file_host_api._FILE_HOST_CACHE._cache[key2] == 'C:/path/two.txt'

    async def test_sync_purges_expired_rows(self, file_host_row_tracker) -> None:
        """同步时物理删除已过期的行"""
        from src.service.omega_file_host import api as file_host_api

        expired_key = uuid.uuid4().hex
        alive_key = uuid.uuid4().hex
        await _seed_row_direct(expired_key, 'C:/path/expired.txt', expired_time=_TEST_DATETIME_PAST)
        await _seed_row_direct(alive_key, 'C:/path/alive.txt')
        file_host_row_tracker.extend([expired_key, alive_key])

        await file_host_api._sync_file_host_cache()

        assert await _query_row_or_none(expired_key) is None
        assert await _query_row_or_none(alive_key) is not None
        assert expired_key not in file_host_api._FILE_HOST_CACHE._cache

    async def test_sync_failure_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """同步失败时异常仅记录日志, 不向上传播"""
        from src.service.omega_file_host import api as file_host_api

        async def _raise_error(*args, **kwargs) -> None:
            raise RuntimeError('sync failed')

        monkeypatch.setattr(file_host_api._FILE_HOST_CACHE, 'sync_internal', _raise_error)

        await file_host_api._sync_file_host_cache()


class TestDownloadEndpoint:
    """文件下载端点测试(直打子应用)"""

    @pytest.fixture(autouse=True)
    def _require_hosting_service(self) -> None:
        from src.service.omega_file_host.config import file_host_config

        if not file_host_config.omega_file_host_enable_hosting_service:
            pytest.skip('文件托管服务未启用')

    async def test_download_hit(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            download_client: AsyncClient,
    ) -> None:
        """命中时 200 返回文件内容(无需任何鉴权 Headers), Content-Type 与 Content-Disposition 正确"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        content = b'test file content \x00\xff\x10'
        resource = AnyResource(str(_make_test_file(tmp_path, content=content)))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)

        response = await download_client.get(f'/download/{file_uuid}')

        assert response.status_code == 200
        assert response.content == content
        assert response.headers['content-type'] == 'application/octet-stream'
        content_disposition = response.headers['content-disposition']
        assert 'attachment' in content_disposition
        assert f'filename="{file_uuid}.txt"' in content_disposition

    async def test_download_missing_returns_404(self, download_client: AsyncClient) -> None:
        response = await download_client.get(f'/download/{uuid.uuid4().hex}')

        assert response.status_code == 404
        assert response.json()['detail'] == 'File expired or deleted'

    async def test_download_file_deleted_returns_404(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            download_client: AsyncClient,
    ) -> None:
        """缓存命中但文件已被删除时返回第二阶段 404"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        file = _make_test_file(tmp_path)
        resource = AnyResource(str(file))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)
        file.unlink()

        response = await download_client.get(f'/download/{file_uuid}')

        assert response.status_code == 404
        assert response.json()['detail'] == 'File not found'

    async def test_download_empty_value_returns_404(
            self,
            file_host_row_tracker,
            download_client: AsyncClient,
    ) -> None:
        """缓存值为空串时按不存在处理(404)"""
        key = uuid.uuid4().hex
        await _seed_row_direct(key, '')
        file_host_row_tracker.append(key)

        response = await download_client.get(f'/download/{key}')

        assert response.status_code == 404

    async def test_download_triggers_refresh(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            download_client: AsyncClient,
    ) -> None:
        """访问下载端点触发滑动续期"""
        file = _make_test_file(tmp_path)
        path_str = str(file.resolve().as_posix())
        key = _make_uuid(path_str)
        await _seed_row_direct(key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000))
        file_host_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        response = await download_client.get(f'/download/{key}')

        assert response.status_code == 200
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_download_post_not_allowed(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            download_client: AsyncClient,
    ) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)

        response = await download_client.post(f'/download/{file_uuid}')

        assert response.status_code == 405

    async def test_download_encoded_slash_no_traversal(self, download_client: AsyncClient) -> None:
        """路径段含编码斜杠时无法匹配路由, 不存在路径穿越"""
        response = await download_client.get('/download/..%2F..%2Fsecret')

        assert response.status_code == 404


class TestProtocol:
    """OmegaFileHostProtocol 托管协议测试(真实数据库)"""

    async def test_get_hosting_path_enabled(
            self,
            tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch,
            file_host_row_tracker,
    ) -> None:
        """服务启用时返回文件下载 URL, 且缓存行已写入"""
        from src.resource import AnyResource
        from src.service.omega_file_host import api as file_host_api
        from src.service.omega_file_host.config import file_host_config

        monkeypatch.setattr(file_host_config, 'omega_file_host_enable_hosting_service', True)

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await resource.get_hosting_path()

        expected_uuid = _make_uuid(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        assert result == f'{file_host_api._FILE_HOST_API.root_url}/download/{expected_uuid}'
        assert await _query_row_or_none(expected_uuid) is not None

    async def test_get_hosting_path_disabled(
            self,
            tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch,
            file_host_row_tracker,
    ) -> None:
        """服务未启用时返回本地文件路径, 且不产生缓存行"""
        from src.resource import AnyResource
        from src.service.omega_file_host.config import file_host_config

        monkeypatch.setattr(file_host_config, 'omega_file_host_enable_hosting_service', False)

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await resource.get_hosting_path()

        expected_uuid = _make_uuid(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        assert result == resource.resolve_path
        assert await _query_row_or_none(expected_uuid) is None

    async def test_get_hosting_path_missing_file_raises(self, tmp_path: Path) -> None:
        """文件不存在时经 check_file 前置校验抛出 ResourceNotFileError"""
        from src.resource import AnyResource, ResourceNotFileError

        with pytest.raises(ResourceNotFileError, match='is not a file'):
            await AnyResource(str(tmp_path / 'missing.txt')).get_hosting_path()

    async def test_get_hosting_path_ttl_delta(
            self,
            tmp_path: Path,
            monkeypatch: pytest.MonkeyPatch,
            file_host_row_tracker,
    ) -> None:
        """ttl_delta 透传至缓存行过期时间"""
        from src.resource import AnyResource
        from src.service.omega_file_host.config import file_host_config

        monkeypatch.setattr(file_host_config, 'omega_file_host_enable_hosting_service', True)

        resource = AnyResource(str(_make_test_file(tmp_path)))

        await resource.get_hosting_path(ttl_delta=-1000)

        expected_uuid = _make_uuid(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        row = await _query_row_or_none(expected_uuid)
        assert row is not None
        expected = datetime.now() + timedelta(seconds=_get_cache_ttl() - 1000)
        assert abs((row.expired_at - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE


class TestGetFileDownloadUrl:
    """get_file_download_url 测试"""

    def test_url_format(self) -> None:
        from src.service import omega_file_host
        from src.service.omega_file_host import api as file_host_api

        file_uuid = uuid.uuid4().hex

        result = omega_file_host.get_file_download_url(file_uuid)

        assert result == f'{file_host_api._FILE_HOST_API.root_url}/download/{file_uuid}'

    def test_url_contains_app_name(self) -> None:
        from src.service import omega_file_host

        result = omega_file_host.get_file_download_url('abc123')

        assert result.startswith('http')
        assert '/omega_file_host/download/abc123' in result
