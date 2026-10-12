"""
@Author         : Ailitonia
@Date           : 2026/9/12 10:00
@FileName       : helpers
@Project        : omega-miya
@Description    : omega core 单元测试共用 helper 函数

    本模块仅放置 test_002_core 目录专属的纯函数 helper, fixture 统一定义在 conftest.py;
    事件/Bot 构造族与跨目录共享 helper 位于 tests/utils.py
    遵守项目约定: `src.*` 导入必须留在函数体内(测试模块在 nonebot 初始化前被收集导入)

@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import delete
from sqlalchemy.exc import NoResultFound

if TYPE_CHECKING:
    from src.database.internal.global_cache import GlobalCache

TEST_DATETIME_PAST = datetime(1990, 1, 1)
"""测试用已过期时间点"""

ASSERT_TIME_TOLERANCE = 2.0
"""时间断言容差(秒), 数据库 DateTime 可能截断到秒"""


def make_uuid5(name: str) -> str:
    """按 omega_global_cache 族模块实现计算指定名称对应的 uuid5 hex(32 位小写十六进制)"""
    return uuid5(namespace=NAMESPACE_URL, name=name).hex


def assert_datetime_close(actual: datetime, expected: datetime, *, tolerance: float = ASSERT_TIME_TOLERANCE) -> None:
    """断言两个时间的偏差在容差内"""
    assert abs((actual - expected).total_seconds()) <= tolerance


def assert_close_to_now(
        target: datetime,
        expected_delta: timedelta,
        *,
        tolerance: float = ASSERT_TIME_TOLERANCE,
) -> None:
    """断言目标时间与 当前时间+expected_delta 的偏差在容差内"""
    assert_datetime_close(target, datetime.now() + expected_delta, tolerance=tolerance)


async def seed_global_cache_row(
        cache_name: str,
        cache_key: str,
        cache_value: str,
        expired_time: datetime | timedelta | None = None,
) -> None:
    """以独立会话直接向数据库写入(或更新)缓存行并提交, 模拟外部写入(不经过被测模块的内存缓存)"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        await dal.add_update_exist(
            cache_name=cache_name,
            cache_key=cache_key,
            cache_value=cache_value,
            expired_time=expired_time,
        )
        await dal.commit_session()


async def query_global_cache_row_or_none(
        cache_name: str,
        cache_key: str,
        *,
        include_expired: bool = True,
) -> 'GlobalCache | None':
    """以独立会话查询缓存行, 不存在返回 None"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        try:
            return await dal.query_unique(cache_name, cache_key, include_expired=include_expired)
        except NoResultFound:
            return None


async def query_all_global_cache_rows(cache_name: str, *, include_expired: bool = True) -> list['GlobalCache']:
    """以独立会话查询指定 cache_name 的全部缓存行"""
    from src.database.internal.global_cache import GlobalCacheDAL

    async with GlobalCacheDAL.create() as dal:
        return await dal.query_series(cache_name, include_expired=include_expired)


async def delete_global_cache_rows(cache_name: str, cache_keys: list[str] | None = None) -> None:
    """物理删除缓存行

    - cache_keys 为 None: 删除指定 cache_name 的全部行(含未过期), 供持有独立命名空间的调用方使用
    - cache_keys 为空列表: 不执行任何操作
    - cache_keys 非空: 仅定点删除指定键, 供测试 import 期注册单例的调用方使用(避免误删其他来源写入的行)
    """
    if cache_keys is not None and not cache_keys:
        return

    from src.database.helpers import database_session
    from src.database.schema import GlobalCacheOrm

    statement = delete(GlobalCacheOrm).where(GlobalCacheOrm.cache_name == cache_name)
    if cache_keys is not None:
        statement = statement.where(GlobalCacheOrm.cache_key.in_(cache_keys))

    async with database_session() as session:
        await session.execute(statement)
