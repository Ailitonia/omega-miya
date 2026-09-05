"""
@Author         : Ailitonia
@Date           : 2026/9/5 15:01
@FileName       : test_005_omega_global_cache
@Project        : omega-miya
@Description    : OmegaGlobalCache 全局缓存单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator, Callable
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.global_cache import GlobalCache
    from src.service.omega_global_cache import OmegaGlobalCache

_TEST_DATETIME_PAST = datetime(1990, 1, 1)
"""测试用已过期时间点"""

_NAME_MAX_LENGTH = 64
"""数据库表 cache_name 字段长度上限 (String(64))"""

_KEY_MAX_LENGTH = 64
"""数据库表 cache_key 字段长度上限 (String(64))"""

_ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


async def _unexpected_query(*args: Any, **kwargs: Any) -> str:
    """打桩用: 不应被调用的数据库查询"""
    raise AssertionError('不应访问数据库')


async def _seed_row(
        cache_name: str,
        cache_key: str,
        cache_value: str,
        expired_time: datetime | timedelta | None = None,
) -> None:
    """以独立会话直接向数据库写入(或更新)缓存行并提交, 模拟外部写入"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        await dal.add_update_exist(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_time=expired_time,
        )
        await dal.commit_session()


async def _query_row_or_none(cache_name: str, cache_key: str, *, include_expired: bool = True) -> 'GlobalCache | None':
    """以独立会话查询缓存行, 不存在返回 None"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        try:
            return await dal.query_unique(cache_name, cache_key, include_expired=include_expired)
        except NoResultFound:
            return None


async def _query_all_rows(cache_name: str, *, include_expired: bool = True) -> list['GlobalCache']:
    """以独立会话查询指定 cache_name 的全部缓存行"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        return await dal.query_series(cache_name, include_expired=include_expired)


async def _delete_cache_rows(cache_name: str) -> None:
    """物理删除指定 cache_name 的全部数据库行(含未过期)"""
    from src.database.helpers import database_session
    from src.database.schema import GlobalCacheOrm

    async with database_session() as session:
        await session.execute(delete(GlobalCacheOrm).where(GlobalCacheOrm.cache_name == cache_name))


def _assert_close_to_now(target: datetime, expected_delta: timedelta) -> None:
    """断言目标时间与 当前时间+expected_delta 的偏差在容差内"""
    expected = datetime.now() + expected_delta
    assert abs((target - expected).total_seconds()) <= _ASSERT_TIME_TOLERANCE


@pytest.fixture
async def cache_factory() -> AsyncGenerator[Callable[..., 'OmegaGlobalCache'], None]:
    """OmegaGlobalCache 实例工厂(自动分配唯一 cache_name), 测试后自动清理全局注册表与数据库行"""
    import src.service.omega_global_cache as cache_module

    created: list[OmegaGlobalCache] = []

    def _factory(cache_name: str | None = None, **kwargs: Any) -> 'OmegaGlobalCache':
        cache = cache_module.OmegaGlobalCache(cache_name or f'test_ogc_{uuid4().hex[:8]}', **kwargs)
        created.append(cache)
        return cache

    yield _factory

    for cache in created:
        cache_module._REGISTERED_CACHE.discard(cache._cache_name)
        await _delete_cache_rows(cache._cache_name)


class TestModuleContract:
    """模块导出契约测试"""

    def test_module_all(self) -> None:
        import src.service.omega_global_cache as cache_module

        assert cache_module.__all__ == ['OmegaGlobalCache']

    def test_registered_cache_container(self) -> None:
        import src.service.omega_global_cache as cache_module

        assert isinstance(cache_module._REGISTERED_CACHE, set)
        assert all(isinstance(x, str) for x in cache_module._REGISTERED_CACHE)

    def test_public_interface(self) -> None:
        import inspect

        from src.service.omega_global_cache import OmegaGlobalCache

        assert inspect.iscoroutinefunction(OmegaGlobalCache.load)
        assert inspect.iscoroutinefunction(OmegaGlobalCache.save)
        assert inspect.iscoroutinefunction(OmegaGlobalCache.sync_internal)
        assert isinstance(OmegaGlobalCache.expired_at, property)
        assert callable(OmegaGlobalCache.set_expired_at)

    def test_init_signature(self) -> None:
        import inspect

        from src.service.omega_global_cache import OmegaGlobalCache

        signature = inspect.signature(OmegaGlobalCache.__init__)
        assert signature.parameters['default_ttl'].default == 86400
        assert signature.parameters['default_ttl'].kind is inspect.Parameter.KEYWORD_ONLY

    def test_max_length_constants_match_schema(self) -> None:
        """长度上限常量应与数据库表字段 String(64) 保持一致, 防止主动校验与 schema 脱节"""
        import src.service.omega_global_cache as cache_module
        from src.database.schema import GlobalCacheOrm

        columns = GlobalCacheOrm.__table__.columns

        assert cache_module._CACHE_NAME_MAX_LENGTH == columns['cache_name'].type.length
        assert cache_module._CACHE_KEY_MAX_LENGTH == columns['cache_key'].type.length


class TestInitAndRegistry:
    """实例化与全局注册表测试"""

    async def test_register_default(self, cache_factory) -> None:
        import src.service.omega_global_cache as cache_module

        cache = cache_factory()

        assert cache._cache_name in cache_module._REGISTERED_CACHE
        assert cache._cache == {}
        assert cache._ttl == 86400

    async def test_register_custom_ttl(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=60)

        assert cache._ttl == 60

    async def test_register_strip_name(self, cache_factory) -> None:
        import src.service.omega_global_cache as cache_module

        name = f'test_ogc_{uuid4().hex[:8]}'
        cache = cache_factory(cache_name=f'  {name}  ')

        assert cache._cache_name == name
        assert name in cache_module._REGISTERED_CACHE

    async def test_register_duplicate_raises(self, cache_factory) -> None:
        from src.service.omega_global_cache import OmegaGlobalCache

        cache = cache_factory()

        with pytest.raises(ValueError, match='already registered'):
            OmegaGlobalCache(cache._cache_name)

    async def test_register_duplicate_after_strip_raises(self, cache_factory) -> None:
        """名称经 strip 归一化后判重, 带空白包装的同名也应被拒绝"""
        from src.service.omega_global_cache import OmegaGlobalCache

        cache = cache_factory()

        with pytest.raises(ValueError, match='already registered'):
            OmegaGlobalCache(f'  {cache._cache_name}  ')

    async def test_register_failure_not_pollute_registry(self, cache_factory) -> None:
        """重复注册失败后, 注册表内容不应发生变化"""
        import src.service.omega_global_cache as cache_module
        from src.service.omega_global_cache import OmegaGlobalCache

        cache = cache_factory()
        snapshot = set(cache_module._REGISTERED_CACHE)

        with pytest.raises(ValueError, match='already registered'):
            OmegaGlobalCache(cache._cache_name)

        assert cache_module._REGISTERED_CACHE == snapshot

    async def test_register_empty_name_raises(self) -> None:
        from src.service.omega_global_cache import OmegaGlobalCache

        with pytest.raises(ValueError, match='Invalid cache_name'):
            OmegaGlobalCache('')

    async def test_register_blank_name_raises(self) -> None:
        """纯空白名称经 strip 后为空, 同样应被拒绝"""
        from src.service.omega_global_cache import OmegaGlobalCache

        with pytest.raises(ValueError, match='Invalid cache_name'):
            OmegaGlobalCache('   ')

    async def test_register_invalid_name_not_pollute_registry(self) -> None:
        """非法名称注册失败后, 空名称不应残留于注册表"""
        import src.service.omega_global_cache as cache_module
        from src.service.omega_global_cache import OmegaGlobalCache

        with pytest.raises(ValueError, match='Invalid cache_name'):
            OmegaGlobalCache('')

        assert '' not in cache_module._REGISTERED_CACHE

    async def test_register_name_max_length(self, cache_factory) -> None:
        """cache_name 长度恰为字段上限 64 字符时可正常注册"""
        name = 'n' * _NAME_MAX_LENGTH
        cache = cache_factory(cache_name=name)

        assert cache._cache_name == name

    async def test_register_name_over_length_raises(self) -> None:
        """cache_name 超过 64 字符时主动抛出 ValueError, 且不污染注册表"""
        import src.service.omega_global_cache as cache_module
        from src.service.omega_global_cache import OmegaGlobalCache

        name = 'n' * (_NAME_MAX_LENGTH + 1)

        with pytest.raises(ValueError, match='Invalid cache_name'):
            OmegaGlobalCache(name)

        assert name not in cache_module._REGISTERED_CACHE

    async def test_register_unicode_name(self, cache_factory) -> None:
        import src.service.omega_global_cache as cache_module

        name = f'测试缓存_{uuid4().hex[:6]}'
        cache = cache_factory(cache_name=name)

        assert cache._cache_name == name
        assert name in cache_module._REGISTERED_CACHE

    async def test_register_zero_and_negative_ttl(self, cache_factory) -> None:
        """ttl 为零或负数时允许注册(行为文档化: 过期时间将位于当前或过去)"""
        cache_zero = cache_factory(default_ttl=0)
        cache_negative = cache_factory(default_ttl=-60)

        assert cache_zero._ttl == 0
        assert cache_negative._ttl == -60

    async def test_multiple_instances_coexist(self, cache_factory) -> None:
        import src.service.omega_global_cache as cache_module

        caches = [cache_factory() for _ in range(3)]

        names = {cache._cache_name for cache in caches}
        assert len(names) == 3
        assert names <= cache_module._REGISTERED_CACHE


class TestExpiryCalculation:
    """过期时间计算测试"""

    async def test_expired_at_default(self, cache_factory) -> None:
        cache = cache_factory()

        expired_at = cache.expired_at

        assert isinstance(expired_at, datetime)
        _assert_close_to_now(expired_at, timedelta(seconds=86400))

    async def test_expired_at_custom_ttl(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=60)

        _assert_close_to_now(cache.expired_at, timedelta(seconds=60))

    async def test_expired_at_refresh_each_access(self, cache_factory) -> None:
        """expired_at 每次访问重新基于当前时间计算, 结果单调不减"""
        cache = cache_factory(default_ttl=3600)

        first = cache.expired_at
        second = cache.expired_at

        assert second >= first

    async def test_set_expired_at_zero_delta(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=3600)

        _assert_close_to_now(cache.set_expired_at(), timedelta(seconds=3600))
        _assert_close_to_now(cache.set_expired_at(ttl_delta=0), timedelta(seconds=3600))

    async def test_set_expired_at_positive_delta(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=3600)

        _assert_close_to_now(cache.set_expired_at(ttl_delta=600), timedelta(seconds=4200))

    async def test_set_expired_at_negative_delta(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=60)

        _assert_close_to_now(cache.set_expired_at(ttl_delta=-30), timedelta(seconds=30))

    async def test_expired_at_zero_ttl(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=0)

        _assert_close_to_now(cache.expired_at, timedelta(seconds=0))


class TestLoad:
    """load 读取行为测试(真实数据库)"""

    async def test_load_miss_returns_none(self, cache_factory) -> None:
        cache = cache_factory()

        assert await cache.load('nonexistent_key') is None

    async def test_load_from_db_and_backfill_memory(self, cache_factory) -> None:
        """内存未命中时从数据库加载, 并回填内存缓存"""
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'key1', 'value1')

        value = await cache.load('key1')

        assert value == 'value1'
        assert cache._cache['key1'] == 'value1'

    async def test_load_memory_hit_skips_db(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """内存命中时直接返回, 不访问数据库"""
        cache = cache_factory()
        cache._cache['key1'] = 'memory_value'
        monkeypatch.setattr(cache, '_query_key_value', _unexpected_query)

        assert await cache.load('key1') == 'memory_value'

    async def test_load_memory_hit_empty_string(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """空字符串值为 falsy, 内存命中判断基于 is not None, 不应被误判为未命中"""
        cache = cache_factory()
        cache._cache['key1'] = ''
        monkeypatch.setattr(cache, '_query_key_value', _unexpected_query)

        assert await cache.load('key1') == ''

    async def test_load_expired_row_returns_none(self, cache_factory) -> None:
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'key1', 'value1', expired_time=_TEST_DATETIME_PAST)

        assert await cache.load('key1') is None

    async def test_load_stale_memory_after_external_update(self, cache_factory) -> None:
        """内存级缓存对象存续期间不失效: 外部更新数据库后, load 仍返回内存中的旧值"""
        cache = cache_factory()
        await cache.save('key1', 'old_value')
        await _seed_row(cache._cache_name, 'key1', 'new_value')

        assert await cache.load('key1') == 'old_value'

    async def test_load_miss_not_cached(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """miss 无负缓存: 连续两次 load 不存在的 key 均会查询数据库"""
        cache = cache_factory()

        call_count = 0

        async def _spy_query(*args: Any, **kwargs: Any) -> str:
            nonlocal call_count
            call_count += 1
            raise NoResultFound

        monkeypatch.setattr(cache, '_query_key_value', _spy_query)

        assert await cache.load('key1') is None
        assert await cache.load('key1') is None
        assert call_count == 2

    async def test_load_db_error_propagates(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """数据库异常(非 NoResultFound)向上传播"""
        cache = cache_factory()

        async def _raise_error(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError('database error')

        monkeypatch.setattr(cache, '_query_key_value', _raise_error)

        with pytest.raises(RuntimeError, match='database error'):
            await cache.load('key1')

    async def test_load_key_max_length(self, cache_factory) -> None:
        """cache_key 长度恰为字段上限 64 字符时可正常读写"""
        cache = cache_factory()
        key = 'k' * _KEY_MAX_LENGTH

        await cache.save(key, 'value1')
        cache._cache.clear()

        assert await cache.load(key) == 'value1'

    async def test_load_key_over_length_raises(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """cache_key 超过 64 字符时主动抛出 ValueError: 优先于内存查询且不访问数据库"""
        cache = cache_factory()
        key = 'k' * (_KEY_MAX_LENGTH + 1)
        cache._cache[key] = 'memory_value'
        monkeypatch.setattr(cache, '_query_key_value', _unexpected_query)

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await cache.load(key)

    async def test_load_empty_key_raises(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """cache_key 为空时主动抛出 ValueError, 且不访问数据库"""
        cache = cache_factory()
        monkeypatch.setattr(cache, '_query_key_value', _unexpected_query)

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await cache.load('')

    async def test_load_long_and_unicode_value_roundtrip(self, cache_factory) -> None:
        """清空内存强制走数据库路径, 验证长文本与 unicode 值往返一致"""
        cache = cache_factory()
        value = f'测试值_{"x" * 10000}'

        await cache.save('key1', value)
        cache._cache.clear()

        assert await cache.load('key1') == value


class TestSave:
    """save 写入行为测试(真实数据库)"""

    async def test_save_persists_to_db(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=3600)

        await cache.save('key1', 'value1')

        row = await _query_row_or_none(cache._cache_name, 'key1')
        assert row is not None
        assert row.cache_value == 'value1'
        _assert_close_to_now(row.expired_at, timedelta(seconds=3600))
        assert cache._cache['key1'] == 'value1'

    async def test_save_upsert_updates_single_row(self, cache_factory) -> None:
        """重复保存同一 key 为更新(upsert)而非插入, 数据库仍只有一行"""
        cache = cache_factory()

        await cache.save('key1', 'value1')
        await cache.save('key1', 'value2')

        rows = await _query_all_rows(cache._cache_name)
        assert len(rows) == 1
        assert rows[0].cache_value == 'value2'
        assert cache._cache['key1'] == 'value2'

    async def test_save_with_positive_ttl_delta(self, cache_factory) -> None:
        cache = cache_factory(default_ttl=3600)

        await cache.save('key1', 'value1', ttl_delta=600)

        row = await _query_row_or_none(cache._cache_name, 'key1')
        assert row is not None
        _assert_close_to_now(row.expired_at, timedelta(seconds=4200))

    async def test_save_immediately_expired(self, cache_factory) -> None:
        """ttl_delta 大负偏移使行立即过期: 内存仍持有值, 数据库默认查询已查不到(内存/库语义分歧边界)"""
        cache = cache_factory(default_ttl=60)

        await cache.save('key1', 'value1', ttl_delta=-3600)

        assert cache._cache['key1'] == 'value1'
        assert await _query_row_or_none(cache._cache_name, 'key1', include_expired=False) is None

        row = await _query_row_or_none(cache._cache_name, 'key1', include_expired=True)
        assert row is not None
        assert row.cache_value == 'value1'

    async def test_save_empty_string_value(self, cache_factory) -> None:
        cache = cache_factory()

        await cache.save('key1', '')

        row = await _query_row_or_none(cache._cache_name, 'key1')
        assert row is not None
        assert row.cache_value == ''
        assert cache._cache['key1'] == ''

    async def test_save_unicode_key_value(self, cache_factory) -> None:
        cache = cache_factory()

        await cache.save('测试键', '测试值 ✓')

        row = await _query_row_or_none(cache._cache_name, '测试键')
        assert row is not None
        assert row.cache_value == '测试值 ✓'
        assert cache._cache['测试键'] == '测试值 ✓'

    async def test_save_long_value(self, cache_factory) -> None:
        cache = cache_factory()
        value = 'v' * 10000

        await cache.save('key1', value)

        row = await _query_row_or_none(cache._cache_name, 'key1')
        assert row is not None
        assert row.cache_value == value

    async def test_save_key_over_length_raises(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """cache_key 超过 64 字符时主动抛出 ValueError, 且不访问数据库、不污染内存"""
        cache = cache_factory()
        key = 'k' * (_KEY_MAX_LENGTH + 1)
        monkeypatch.setattr(cache, '_upsert_key_value', _unexpected_query)

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await cache.save(key, 'value1')

        assert key not in cache._cache

    async def test_save_empty_key_raises(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """cache_key 为空时主动抛出 ValueError, 且不访问数据库、不污染内存"""
        cache = cache_factory()
        monkeypatch.setattr(cache, '_upsert_key_value', _unexpected_query)

        with pytest.raises(ValueError, match='Invalid cache_key'):
            await cache.save('', 'value1')

        assert '' not in cache._cache

    async def test_save_returns_none(self, cache_factory) -> None:
        cache = cache_factory()

        assert await cache.save('key1', 'value1') is None

    async def test_save_failure_not_pollute_memory(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """写库失败时异常向上传播, 且内存缓存不被污染"""
        cache = cache_factory()

        async def _raise_error(*args: Any, **kwargs: Any) -> str:
            raise RuntimeError('upsert failed')

        monkeypatch.setattr(cache, '_upsert_key_value', _raise_error)

        with pytest.raises(RuntimeError, match='upsert failed'):
            await cache.save('key1', 'value1')

        assert 'key1' not in cache._cache


class TestSyncInternal:
    """sync_internal 内存/数据库同步行为测试(真实数据库)"""

    async def test_sync_returns_none(self, cache_factory) -> None:
        cache = cache_factory()

        assert await cache.sync_internal() is None

    async def test_sync_removes_memory_only_entry(self, cache_factory) -> None:
        """内存中独有的项(数据库不存在)在同步后被清除"""
        cache = cache_factory()
        cache._cache['ghost'] = 'x'

        await cache.sync_internal()

        assert 'ghost' not in cache._cache

    async def test_sync_backfills_from_db(self, cache_factory) -> None:
        """数据库中独有的项在同步后回填内存"""
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'db_key', 'db_value')
        assert 'db_key' not in cache._cache

        await cache.sync_internal()

        assert cache._cache['db_key'] == 'db_value'

    async def test_sync_deletes_expired_rows(self, cache_factory) -> None:
        """同步时物理删除本 cache_name 下已过期的行, 保留未过期行"""
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'expired_key', 'v1', expired_time=_TEST_DATETIME_PAST)
        await _seed_row(cache._cache_name, 'alive_key', 'v2')

        await cache.sync_internal()

        rows = await _query_all_rows(cache._cache_name, include_expired=True)
        assert [row.cache_key for row in rows] == ['alive_key']

    async def test_sync_does_not_affect_other_cache(self, cache_factory) -> None:
        """过期行清理仅作用于本 cache_name, 不影响其他 cache_name 的行"""
        cache = cache_factory()
        other = cache_factory()
        await _seed_row(cache._cache_name, 'expired_key', 'v1', expired_time=_TEST_DATETIME_PAST)
        await _seed_row(other._cache_name, 'expired_key', 'v2', expired_time=_TEST_DATETIME_PAST)

        await cache.sync_internal()

        assert await _query_all_rows(cache._cache_name, include_expired=True) == []

        other_rows = await _query_all_rows(other._cache_name, include_expired=True)
        assert len(other_rows) == 1
        assert other_rows[0].cache_key == 'expired_key'

    async def test_sync_memory_matches_db(self, cache_factory) -> None:
        """同步后内存缓存与数据库未过期行完全一致"""
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'k1', 'v1')
        await _seed_row(cache._cache_name, 'k2', 'v2', expired_time=_TEST_DATETIME_PAST)
        cache._cache['stale'] = 'x'

        await cache.sync_internal()

        assert cache._cache == {'k1': 'v1'}

    async def test_sync_empty(self, cache_factory) -> None:
        """数据库无行时同步, 内存缓存被清空"""
        cache = cache_factory()

        await cache.sync_internal()

        assert cache._cache == {}


class TestPrivateDalIntegration:
    """私有方法与 GlobalCacheDAL 协作测试(真实数据库)"""

    async def test_query_key_value(self, cache_factory) -> None:
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'key1', 'value1')

        assert await cache._query_key_value('key1') == 'value1'

    async def test_query_key_value_not_found_raises(self, cache_factory) -> None:
        cache = cache_factory()

        with pytest.raises(NoResultFound):
            await cache._query_key_value('missing_key')

    async def test_query_key_value_include_expired(self, cache_factory) -> None:
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'key1', 'value1', expired_time=_TEST_DATETIME_PAST)

        with pytest.raises(NoResultFound):
            await cache._query_key_value('key1')

        assert await cache._query_key_value('key1', include_expired=True) == 'value1'

    async def test_query_all_values(self, cache_factory) -> None:
        cache = cache_factory()
        await _seed_row(cache._cache_name, 'k1', 'v1')
        await _seed_row(cache._cache_name, 'k2', 'v2', expired_time=_TEST_DATETIME_PAST)

        assert await cache._query_all_values() == {'k1': 'v1'}
        assert await cache._query_all_values(include_expired=True) == {'k1': 'v1', 'k2': 'v2'}

    async def test_query_all_values_empty(self, cache_factory) -> None:
        cache = cache_factory()

        assert await cache._query_all_values() == {}

    async def test_clean_db_expired_scope(self, cache_factory) -> None:
        """_clean_db_expired 仅清理本 cache_name 的过期行"""
        cache = cache_factory()
        other = cache_factory()
        await _seed_row(cache._cache_name, 'expired_key', 'v1', expired_time=_TEST_DATETIME_PAST)
        await _seed_row(cache._cache_name, 'alive_key', 'v2')
        await _seed_row(other._cache_name, 'expired_key', 'v3', expired_time=_TEST_DATETIME_PAST)

        await cache._clean_db_expired()

        own_rows = await _query_all_rows(cache._cache_name, include_expired=True)
        assert [row.cache_key for row in own_rows] == ['alive_key']
        assert len(await _query_all_rows(other._cache_name, include_expired=True)) == 1

    async def test_upsert_key_value_insert_and_update(self, cache_factory) -> None:
        cache = cache_factory()

        assert await cache._upsert_key_value('key1', 'v1') == 'v1'
        assert await cache._upsert_key_value('key1', 'v2') == 'v2'

        rows = await _query_all_rows(cache._cache_name)
        assert len(rows) == 1
        assert rows[0].cache_value == 'v2'


class TestEndToEnd:
    """端到端组合行为测试(真实数据库)"""

    async def test_save_clear_memory_load(self, cache_factory) -> None:
        """save 后清空内存, load 从数据库路径取回一致值"""
        cache = cache_factory()

        await cache.save('key1', 'value1')
        cache._cache.clear()

        assert await cache.load('key1') == 'value1'

    async def test_save_sync_load(self, cache_factory, monkeypatch: pytest.MonkeyPatch) -> None:
        """save 后执行同步, 之后 load 命中内存不再访问数据库"""
        cache = cache_factory()

        await cache.save('key1', 'value1')
        await cache.sync_internal()

        monkeypatch.setattr(cache, '_query_key_value', _unexpected_query)
        assert await cache.load('key1') == 'value1'

    async def test_two_caches_isolated(self, cache_factory) -> None:
        """不同 cache_name 的实例数据相互隔离, 同名 key 互不干扰"""
        cache1 = cache_factory()
        cache2 = cache_factory()

        await cache1.save('same_key', 'value1')
        await cache2.save('same_key', 'value2')
        cache1._cache.clear()
        cache2._cache.clear()

        assert await cache1.load('same_key') == 'value1'
        assert await cache2.load('same_key') == 'value2'
