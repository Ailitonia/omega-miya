"""
@Author         : Ailitonia
@Date           : 2026/9/5 16:19
@FileName       : test_007_omega_short_link
@Project        : omega-miya
@Description    : omega_short_link 单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.global_cache import GlobalCache

_SHORT_LINK_CACHE_NAME = 'omega_short_link'
"""被测模块使用的全局缓存名称"""

_TEST_DATETIME_PAST = datetime(1990, 1, 1)
"""测试用已过期时间点"""

_ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


def _make_uuid(url: str) -> str:
    """按模块实现计算指定 URL 对应的短链接 UUID"""
    return uuid.uuid5(namespace=uuid.NAMESPACE_URL, name=url).hex


def _make_unique_url() -> str:
    """生成测试用唯一 URL(保证缓存键唯一, 避免用例间干扰)"""
    return f'https://example.com/t/{uuid.uuid4().hex}'


async def _seed_row_direct(cache_key: str, cache_value: str, expired_time: datetime | timedelta | None = None) -> None:
    """经 DAL 直接写入缓存行并提交(不经过被测模块的内存缓存)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        await dal.add_update_exist(
            cache_name=_SHORT_LINK_CACHE_NAME,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_time=expired_time,
        )
        await dal.commit_session()


async def _query_row_or_none(cache_key: str, *, include_expired: bool = True) -> 'GlobalCache | None':
    """以独立会话查询短链接缓存行, 不存在返回 None"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        try:
            return await dal.query_unique(_SHORT_LINK_CACHE_NAME, cache_key, include_expired=include_expired)
        except NoResultFound:
            return None


async def _query_all_keys() -> set[str]:
    """以独立会话查询短链接缓存全部键(含已过期)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        rows = await dal.query_series(_SHORT_LINK_CACHE_NAME, include_expired=True)
    return {row.cache_key for row in rows}


async def _delete_short_link_rows(cache_keys: list[str]) -> None:
    """物理删除指定的短链接缓存行"""
    if not cache_keys:
        return

    from src.database.helpers import database_session
    from src.database.schema import GlobalCacheOrm

    async with database_session() as session:
        await session.execute(
            delete(GlobalCacheOrm)
            .where(GlobalCacheOrm.cache_name == _SHORT_LINK_CACHE_NAME)
            .where(GlobalCacheOrm.cache_key.in_(cache_keys))
        )


@pytest.fixture
async def short_link_row_tracker() -> AsyncGenerator[list[str], None]:
    """跟踪测试产生的短链接缓存键, 测试后定点清理数据库行(模块单例不注销)"""
    created: list[str] = []

    yield created

    await _delete_short_link_rows(created)


@pytest.fixture
async def forward_client() -> AsyncGenerator[AsyncClient, None]:
    """直打短链接子应用的 HTTP 客户端(免 token 校验)"""
    from src.service.omega_short_link import api as short_link_api

    async with AsyncClient(
            transport=ASGITransport(app=short_link_api._SHORT_LINK_API._app),
            base_url='http://testserver',
    ) as client:
        yield client


class TestModuleContract:
    """模块导出与单例契约测试"""

    def test_module_all(self) -> None:
        from src.service import omega_short_link

        assert omega_short_link.__all__ == ['query_short_link_real_url', 'query_short_link_uuid']

    def test_exported_functions(self) -> None:
        import inspect

        from src.service import omega_short_link

        assert inspect.iscoroutinefunction(omega_short_link.query_short_link_uuid)
        assert inspect.iscoroutinefunction(omega_short_link.query_short_link_real_url)
        assert inspect.signature(omega_short_link.query_short_link_uuid).return_annotation is str
        assert inspect.signature(omega_short_link.query_short_link_real_url).return_annotation == str | None

    def test_short_link_api_contract(self) -> None:
        from src.service.omega_short_link import api as short_link_api

        assert short_link_api._SHORT_LINK_API._app_name == 'omega_short_link'
        assert short_link_api._SHORT_LINK_API._enable_token_verify is False

    def test_short_link_cache_contract(self) -> None:
        from src.service.omega_short_link import api as short_link_api
        from src.service.omega_short_link.config import short_link_config

        assert short_link_api._SHORT_LINK_CACHE._cache_name == 'omega_short_link'
        assert short_link_api._SHORT_LINK_CACHE._ttl == short_link_config.omega_short_link_cache_ttl

    def test_sync_job_registered(self) -> None:
        from src.service.apscheduler import scheduler

        job = scheduler.get_job('omega_short_link_sync_short_link_cache')

        assert job is not None

    def test_forward_route_registered(self) -> None:
        """转发服务启用时, 跳转路由应已注册到子应用"""
        from src.service.omega_short_link import api as short_link_api
        from src.service.omega_short_link.config import short_link_config

        if not short_link_config.omega_short_link_enable_http_forward_service:
            pytest.skip('短链接转发服务未启用')

        routes = [route for route in short_link_api._SHORT_LINK_API._app.routes
                  if getattr(route, 'path', None) == '/go/{link_uuid}']
        assert len(routes) == 1
        assert 'GET' in routes[0].methods


class TestQueryShortLinkUuid:
    """query_short_link_uuid 测试(真实数据库)"""

    async def test_returns_uuid_hex(self, short_link_row_tracker) -> None:
        """返回值应为 URL 对应的 uuid5 hex(32 位小写十六进制), 而非 URL 本身"""
        from src.service import omega_short_link

        url = _make_unique_url()

        result = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(result)

        assert result == _make_uuid(url)
        assert result != url
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

    async def test_deterministic(self, short_link_row_tracker) -> None:
        """相同 URL 多次调用返回相同 UUID"""
        from src.service import omega_short_link

        url = _make_unique_url()

        first = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(first)
        second = await omega_short_link.query_short_link_uuid(url)

        assert first == second

    async def test_distinct_urls_distinct_uuids(self, short_link_row_tracker) -> None:
        from src.service import omega_short_link

        uuid1 = await omega_short_link.query_short_link_uuid(_make_unique_url())
        short_link_row_tracker.append(uuid1)
        uuid2 = await omega_short_link.query_short_link_uuid(_make_unique_url())
        short_link_row_tracker.append(uuid2)

        assert uuid1 != uuid2

    async def test_persists_row_with_default_ttl(self, short_link_row_tracker) -> None:
        from src.service import omega_short_link
        from src.service.omega_short_link.config import short_link_config

        url = _make_unique_url()

        result = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(result)

        row = await _query_row_or_none(result)
        assert row is not None
        assert row.cache_key == result
        assert row.cache_value == url
        expected = datetime.now() + timedelta(seconds=short_link_config.omega_short_link_cache_ttl)
        assert abs((row.expired_at - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_ttl_delta_applied(self, short_link_row_tracker) -> None:
        from src.service import omega_short_link
        from src.service.omega_short_link.config import short_link_config

        url = _make_unique_url()

        result = await omega_short_link.query_short_link_uuid(url, ttl_delta=-1000)
        short_link_row_tracker.append(result)

        row = await _query_row_or_none(result)
        assert row is not None
        expected = datetime.now() + timedelta(seconds=short_link_config.omega_short_link_cache_ttl - 1000)
        assert abs((row.expired_at - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_same_url_upsert_single_row(self, short_link_row_tracker) -> None:
        """相同 URL 重复调用为更新而非插入"""
        from src.service import omega_short_link

        url = _make_unique_url()

        first = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(first)
        second = await omega_short_link.query_short_link_uuid(url)

        assert first == second
        all_keys = await _query_all_keys()
        assert sum(1 for key in all_keys if key == first) == 1

    async def test_empty_url_raises(self, short_link_row_tracker) -> None:
        """空 URL 主动抛出 ValueError, 且不产生缓存行"""
        from src.service import omega_short_link

        with pytest.raises(ValueError, match='Invalid url'):
            await omega_short_link.query_short_link_uuid('')

        short_link_row_tracker.append(_make_uuid(''))
        assert await _query_row_or_none(_make_uuid('')) is None

    async def test_blank_url_raises(self) -> None:
        """纯空白 URL 主动抛出 ValueError"""
        from src.service import omega_short_link

        with pytest.raises(ValueError, match='Invalid url'):
            await omega_short_link.query_short_link_uuid('   ')

    async def test_unicode_url(self, short_link_row_tracker) -> None:
        from src.service import omega_short_link

        url = f'https://example.com/测试路径/{uuid.uuid4().hex}'

        result = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(result)

        assert result == _make_uuid(url)
        row = await _query_row_or_none(result)
        assert row is not None
        assert row.cache_value == url


class TestQueryShortLinkRealUrl:
    """query_short_link_real_url 测试(真实数据库)"""

    async def test_load_existing(self, short_link_row_tracker) -> None:
        from src.service import omega_short_link

        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url)
        short_link_row_tracker.append(key)

        assert await omega_short_link.query_short_link_real_url(key) == url

    async def test_load_missing_returns_none(self) -> None:
        from src.service import omega_short_link

        assert await omega_short_link.query_short_link_real_url(_make_uuid(_make_unique_url())) is None

    async def test_auto_refresh_extends_expiry(self, short_link_row_tracker) -> None:
        """auto_refresh=True(默认)命中时滑动续期, expired_at 延后"""
        from src.service import omega_short_link

        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url, expired_time=timedelta(seconds=2592000 - 1000))
        short_link_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        result = await omega_short_link.query_short_link_real_url(key)

        assert result == url
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_no_refresh_keeps_expiry(self, short_link_row_tracker) -> None:
        """auto_refresh=False 命中时不续期, expired_at 不变"""
        from src.service import omega_short_link

        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url, expired_time=timedelta(seconds=2592000 - 1000))
        short_link_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        result = await omega_short_link.query_short_link_real_url(key, auto_refresh=False)

        assert result == url
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert abs((row_after.expired_at - row_before.expired_at).total_seconds()) <= _ASSERT_TIME_TOLERANCE

    async def test_refresh_missing_creates_no_row(self, short_link_row_tracker) -> None:
        """auto_refresh 对不存在的键不产生任何缓存行"""
        from src.service import omega_short_link

        key = _make_uuid(_make_unique_url())
        short_link_row_tracker.append(key)

        assert await omega_short_link.query_short_link_real_url(key) is None
        assert await _query_row_or_none(key) is None

    async def test_expired_row_returns_none(self, short_link_row_tracker) -> None:
        """已过期行返回 None, 且不触发续期"""
        from src.service import omega_short_link

        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url, expired_time=_TEST_DATETIME_PAST)
        short_link_row_tracker.append(key)

        assert await omega_short_link.query_short_link_real_url(key) is None

        row = await _query_row_or_none(key)
        assert row is not None
        assert row.expired_at == _TEST_DATETIME_PAST

    async def test_empty_uuid_raises(self) -> None:
        """空 UUID 经由全局缓存键校验抛出 ValueError"""
        from src.service import omega_short_link

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await omega_short_link.query_short_link_real_url('')

    async def test_refresh_returns_same_value(self, short_link_row_tracker) -> None:
        """续期不改变返回值内容"""
        from src.service import omega_short_link

        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url)
        short_link_row_tracker.append(key)

        first = await omega_short_link.query_short_link_real_url(key)
        second = await omega_short_link.query_short_link_real_url(key)

        assert first == url
        assert second == url


class TestSyncJob:
    """_sync_short_link_cache 定时同步任务测试(真实数据库)"""

    async def test_sync_loads_db_rows(self, short_link_row_tracker) -> None:
        """同步后内存缓存与数据库一致"""
        from src.service.omega_short_link import api as short_link_api

        key1 = _make_uuid(_make_unique_url())
        key2 = _make_uuid(_make_unique_url())
        await _seed_row_direct(key1, 'value1')
        await _seed_row_direct(key2, 'value2')
        short_link_row_tracker.extend([key1, key2])

        assert await short_link_api._sync_short_link_cache() is None

        assert short_link_api._SHORT_LINK_CACHE._cache[key1] == 'value1'
        assert short_link_api._SHORT_LINK_CACHE._cache[key2] == 'value2'

    async def test_sync_purges_expired_rows(self, short_link_row_tracker) -> None:
        """同步时物理删除已过期的行"""
        from src.service.omega_short_link import api as short_link_api

        expired_key = _make_uuid(_make_unique_url())
        alive_key = _make_uuid(_make_unique_url())
        await _seed_row_direct(expired_key, 'expired_value', expired_time=_TEST_DATETIME_PAST)
        await _seed_row_direct(alive_key, 'alive_value')
        short_link_row_tracker.extend([expired_key, alive_key])

        await short_link_api._sync_short_link_cache()

        assert await _query_row_or_none(expired_key) is None
        assert await _query_row_or_none(alive_key) is not None
        assert expired_key not in short_link_api._SHORT_LINK_CACHE._cache

    async def test_sync_failure_swallowed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """同步失败时异常仅记录日志, 不向上传播"""
        from src.service.omega_short_link import api as short_link_api

        async def _raise_error(*args, **kwargs) -> None:
            raise RuntimeError('sync failed')

        monkeypatch.setattr(short_link_api._SHORT_LINK_CACHE, 'sync_internal', _raise_error)

        await short_link_api._sync_short_link_cache()


class TestForwardEndpoint:
    """短链接跳转端点测试(直打子应用)"""

    @pytest.fixture(autouse=True)
    def _require_forward_service(self) -> None:
        from src.service.omega_short_link.config import short_link_config

        if not short_link_config.omega_short_link_enable_http_forward_service:
            pytest.skip('短链接转发服务未启用')

    async def test_redirect_hit(
            self,
            short_link_row_tracker,
            forward_client: AsyncClient,
    ) -> None:
        """命中时 307 重定向且 Location 为真实 URL(无需任何鉴权 Headers)"""
        from src.service import omega_short_link

        url = _make_unique_url()
        link_uuid = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(link_uuid)

        response = await forward_client.get(f'/go/{link_uuid}', follow_redirects=False)

        assert response.status_code == 307
        assert response.headers['location'] == url

    async def test_redirect_missing_returns_404(self, forward_client: AsyncClient) -> None:
        response = await forward_client.get(f'/go/{_make_uuid(_make_unique_url())}', follow_redirects=False)

        assert response.status_code == 404
        assert response.json()['detail'] == 'Short link expired or deleted'

    async def test_redirect_preserves_complex_url(
            self,
            short_link_row_tracker,
            forward_client: AsyncClient,
    ) -> None:
        """Location 原样保留带 query 参数与特殊字符的 URL"""
        from src.service import omega_short_link

        url = f'https://example.com/t/{uuid.uuid4().hex}?a=1&b=%E6%B5%8B%E8%AF%95#frag'
        link_uuid = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(link_uuid)

        response = await forward_client.get(f'/go/{link_uuid}', follow_redirects=False)

        assert response.status_code == 307
        assert response.headers['location'] == url

    async def test_redirect_triggers_refresh(
            self,
            short_link_row_tracker,
            forward_client: AsyncClient,
    ) -> None:
        """访问跳转端点触发滑动续期"""
        url = _make_unique_url()
        key = _make_uuid(url)
        await _seed_row_direct(key, url, expired_time=timedelta(seconds=2592000 - 1000))
        short_link_row_tracker.append(key)
        row_before = await _query_row_or_none(key)
        assert row_before is not None

        response = await forward_client.get(f'/go/{key}', follow_redirects=False)

        assert response.status_code == 307
        row_after = await _query_row_or_none(key)
        assert row_after is not None
        assert row_after.expired_at - row_before.expired_at >= timedelta(seconds=900)

    async def test_redirect_empty_value_returns_404(
            self,
            short_link_row_tracker,
            forward_client: AsyncClient,
    ) -> None:
        """缓存值为空串时处理器按不存在处理(404)"""
        key = _make_uuid(_make_unique_url())
        await _seed_row_direct(key, '')
        short_link_row_tracker.append(key)

        response = await forward_client.get(f'/go/{key}', follow_redirects=False)

        assert response.status_code == 404

    async def test_redirect_post_not_allowed(
            self,
            short_link_row_tracker,
            forward_client: AsyncClient,
    ) -> None:
        from src.service import omega_short_link

        url = _make_unique_url()
        link_uuid = await omega_short_link.query_short_link_uuid(url)
        short_link_row_tracker.append(link_uuid)

        response = await forward_client.post(f'/go/{link_uuid}')

        assert response.status_code == 405
