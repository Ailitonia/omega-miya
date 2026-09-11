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
from datetime import timedelta
from pathlib import Path

import pytest
from async_asgi_testclient import TestClient

from tests.test_002_core.helpers import (
    TEST_DATETIME_PAST,
    assert_close_to_now,
    assert_datetime_close,
    make_uuid5,
    query_all_global_cache_rows,
    query_global_cache_row_or_none,
    seed_global_cache_row,
)

_FILE_HOST_CACHE_NAME = 'omega_file_host'
"""被测模块使用的全局缓存名称"""

_DOWNLOAD_PATH_PREFIX = '/omega_file_host'
"""文件托管子应用在主应用上的挂载前缀"""


def _make_test_file(tmp_path: Path, name: str = 'test_file.txt', content: bytes = b'test file content') -> Path:
    """在临时目录创建已知内容的测试文件"""
    file = tmp_path / name
    file.write_bytes(content)
    return file


def _get_cache_ttl() -> int:
    """获取配置的文件托管缓存时间"""
    from src.service.omega_file_host.config import file_host_config

    return file_host_config.omega_file_host_cache_ttl


@pytest.fixture
def file_host_row_tracker(global_cache_row_tracker_factory) -> list[str]:
    """跟踪测试产生的文件托管缓存键, 测试后定点清理数据库行(模块单例不注销)"""
    return global_cache_row_tracker_factory(_FILE_HOST_CACHE_NAME)


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

        assert result == make_uuid5(resource.resolve_path)
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

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

        row = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, result)
        assert row is not None
        assert row.cache_key == result
        assert row.cache_value == resource.resolve_path
        assert_close_to_now(row.expired_at, timedelta(seconds=_get_cache_ttl()))

    async def test_ttl_delta_applied(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        result = await omega_file_host.query_file_uuid(resource, ttl_delta=-1000)
        file_host_row_tracker.append(result)

        row = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, result)
        assert row is not None
        assert_close_to_now(row.expired_at, timedelta(seconds=_get_cache_ttl() - 1000))

    async def test_same_file_upsert_single_row(self, tmp_path: Path, file_host_row_tracker) -> None:
        """相同文件重复注册为更新而非插入"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))

        first = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(first)
        second = await omega_file_host.query_file_uuid(resource)

        assert first == second
        all_keys = {row.cache_key for row in await query_all_global_cache_rows(_FILE_HOST_CACHE_NAME)}
        assert sum(1 for key in all_keys if key == first) == 1

    @pytest.mark.parametrize('path_kind', ['missing', 'directory'])
    async def test_invalid_path_raises(self, tmp_path: Path, path_kind: str) -> None:
        """不存在的路径或目录路径主动抛出 ValueError"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        path = tmp_path / 'missing.txt' if path_kind == 'missing' else tmp_path

        with pytest.raises(ValueError, match='Invalid file'):
            await omega_file_host.query_file_uuid(AnyResource(str(path)))

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
        assert result == make_uuid5(target_resource.resolve_path)
        row = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, result)
        assert row is not None
        assert row.cache_value == target_resource.resolve_path


class TestQueryFileRealPath:
    """query_file_real_path 测试(真实数据库)"""

    async def test_load_existing(self, tmp_path: Path, file_host_row_tracker) -> None:
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = make_uuid5(path_str)
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, key, path_str)
        file_host_row_tracker.append(key)

        assert await omega_file_host.query_file_real_path(key) == path_str

    async def test_load_missing_returns_none(self) -> None:
        from src.service import omega_file_host

        assert await omega_file_host.query_file_real_path(uuid.uuid4().hex) is None

    async def test_auto_refresh_extends_expiry(self, tmp_path: Path, file_host_row_tracker) -> None:
        """auto_refresh=True(默认)命中时滑动续期, expired_at 延后"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = make_uuid5(path_str)
        await seed_global_cache_row(
            _FILE_HOST_CACHE_NAME, key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000)
        )
        file_host_row_tracker.append(key)
        row_before = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_before is not None

        result = await omega_file_host.query_file_real_path(key)

        assert result == path_str
        row_after = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_no_refresh_keeps_expiry(self, tmp_path: Path, file_host_row_tracker) -> None:
        """auto_refresh=False 命中时不续期, expired_at 不变"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = make_uuid5(path_str)
        await seed_global_cache_row(
            _FILE_HOST_CACHE_NAME, key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000)
        )
        file_host_row_tracker.append(key)
        row_before = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_before is not None

        result = await omega_file_host.query_file_real_path(key, auto_refresh=False)

        assert result == path_str
        row_after = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_after is not None
        assert_datetime_close(row_after.expired_at, row_before.expired_at)

    async def test_expired_row_returns_none(self, tmp_path: Path, file_host_row_tracker) -> None:
        """已过期行返回 None, 且不触发续期"""
        from src.service import omega_file_host

        path_str = str(tmp_path / 'file.txt')
        key = make_uuid5(path_str)
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, key, path_str, expired_time=TEST_DATETIME_PAST)
        file_host_row_tracker.append(key)

        assert await omega_file_host.query_file_real_path(key) is None

        row = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row is not None
        assert row.expired_at == TEST_DATETIME_PAST

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
        assert await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key) is None


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
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, key1, 'C:/path/one.txt')
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, key2, 'C:/path/two.txt')
        file_host_row_tracker.extend([key1, key2])

        assert await file_host_api._sync_file_host_cache() is None

        assert file_host_api._FILE_HOST_CACHE._cache[key1] == 'C:/path/one.txt'
        assert file_host_api._FILE_HOST_CACHE._cache[key2] == 'C:/path/two.txt'

    async def test_sync_purges_expired_rows(self, file_host_row_tracker) -> None:
        """同步时物理删除已过期的行"""
        from src.service.omega_file_host import api as file_host_api

        expired_key = uuid.uuid4().hex
        alive_key = uuid.uuid4().hex
        await seed_global_cache_row(
            _FILE_HOST_CACHE_NAME, expired_key, 'C:/path/expired.txt', expired_time=TEST_DATETIME_PAST
        )
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, alive_key, 'C:/path/alive.txt')
        file_host_row_tracker.extend([expired_key, alive_key])

        await file_host_api._sync_file_host_cache()

        assert await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, expired_key) is None
        assert await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, alive_key) is not None
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
            mounted_app_client: TestClient,
    ) -> None:
        """命中时 200 返回文件内容(无需任何鉴权 Headers), Content-Type 与 Content-Disposition 正确"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        content = b'test file content \x00\xff\x10'
        resource = AnyResource(str(_make_test_file(tmp_path, content=content)))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)

        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/{file_uuid}')

        assert response.status_code == 200
        assert response.content == content
        assert response.headers['content-type'] == 'application/octet-stream'
        content_disposition = response.headers['content-disposition']
        assert 'attachment' in content_disposition
        assert f'filename="{file_uuid}.txt"' in content_disposition

    async def test_download_missing_returns_404(self, mounted_app_client: TestClient) -> None:
        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/{uuid.uuid4().hex}')

        assert response.status_code == 404
        assert response.json()['detail'] == 'File expired or deleted'

    async def test_download_file_deleted_returns_404(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            mounted_app_client: TestClient,
    ) -> None:
        """缓存命中但文件已被删除时返回第二阶段 404"""
        from src.resource import AnyResource
        from src.service import omega_file_host

        file = _make_test_file(tmp_path)
        resource = AnyResource(str(file))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)
        file.unlink()

        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/{file_uuid}')

        assert response.status_code == 404
        assert response.json()['detail'] == 'File not found'

    async def test_download_empty_value_returns_404(
            self,
            file_host_row_tracker,
            mounted_app_client: TestClient,
    ) -> None:
        """缓存值为空串时按不存在处理(404)"""
        key = uuid.uuid4().hex
        await seed_global_cache_row(_FILE_HOST_CACHE_NAME, key, '')
        file_host_row_tracker.append(key)

        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/{key}')

        assert response.status_code == 404

    async def test_download_triggers_refresh(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            mounted_app_client: TestClient,
    ) -> None:
        """访问下载端点触发滑动续期"""
        file = _make_test_file(tmp_path)
        path_str = str(file.resolve().as_posix())
        key = make_uuid5(path_str)
        await seed_global_cache_row(
            _FILE_HOST_CACHE_NAME, key, path_str, expired_time=timedelta(seconds=_get_cache_ttl() - 1000)
        )
        file_host_row_tracker.append(key)
        row_before = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_before is not None

        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/{key}')

        assert response.status_code == 200
        row_after = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_download_post_not_allowed(
            self,
            tmp_path: Path,
            file_host_row_tracker,
            mounted_app_client: TestClient,
    ) -> None:
        from src.resource import AnyResource
        from src.service import omega_file_host

        resource = AnyResource(str(_make_test_file(tmp_path)))
        file_uuid = await omega_file_host.query_file_uuid(resource)
        file_host_row_tracker.append(file_uuid)

        response = await mounted_app_client.post(f'{_DOWNLOAD_PATH_PREFIX}/download/{file_uuid}')

        assert response.status_code == 405

    async def test_download_encoded_slash_no_traversal(self, mounted_app_client: TestClient) -> None:
        """路径段含编码斜杠时不存在路径穿越

        测试客户端不对 scope path 做百分号解码, `..%2F..%2Fsecret` 作为单一路径段命中
        `/download/{file_id}` 路由, 但该值不是已登记的文件 UUID, 缓存未命中返回 404
        """
        response = await mounted_app_client.get(f'{_DOWNLOAD_PATH_PREFIX}/download/..%2F..%2Fsecret')

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

        expected_uuid = make_uuid5(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        assert result == f'{file_host_api._FILE_HOST_API.root_url}/download/{expected_uuid}'
        assert await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, expected_uuid) is not None

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

        expected_uuid = make_uuid5(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        assert result == resource.resolve_path
        assert await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, expected_uuid) is None

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

        expected_uuid = make_uuid5(resource.resolve_path)
        file_host_row_tracker.append(expected_uuid)
        row = await query_global_cache_row_or_none(_FILE_HOST_CACHE_NAME, expected_uuid)
        assert row is not None
        assert_close_to_now(row.expired_at, timedelta(seconds=_get_cache_ttl() - 1000))


class TestGetFileDownloadUrl:
    """get_file_download_url 测试"""

    def test_url_format(self) -> None:
        """URL 由子应用 root_url(含 app_name 前缀)与 /download/{file_uuid} 路径拼接而成"""
        from src.service import omega_file_host
        from src.service.omega_file_host import api as file_host_api

        file_uuid = uuid.uuid4().hex

        result = omega_file_host.get_file_download_url(file_uuid)

        assert f'/omega_file_host/download/{file_uuid}' in result
        assert result == f'{file_host_api._FILE_HOST_API.root_url}/download/{file_uuid}'
