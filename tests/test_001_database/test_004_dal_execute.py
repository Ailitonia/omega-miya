"""
@Author         : Ailitonia
@Date           : 2026/09/03 01:10
@FileName       : test_base_model.py
@Project        : omega-miya
@Description    : src/database/model.py DAL 基类工具方法与会话事务契约单元测试

注意: 所有 src.* 的导入一律放在 fixture/测试函数体内, 原因见 tests/test_001_database/conftest.py
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import random
import string
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError, NoResultFound


def _random_string(k: int = 8) -> str:
    return ''.join(random.sample(string.ascii_letters + string.digits, k=k))


class _FakePostgresqlError(Exception):
    """模拟 asyncpg/psycopg 驱动错误 (携带 sqlstate)"""

    def __init__(self, sqlstate: str) -> None:
        super().__init__('fake postgresql error')
        self.sqlstate = sqlstate


class _FakeSqliteError(Exception):
    """模拟 sqlite3 驱动错误 (携带 extended error code)"""

    def __init__(self, code: int) -> None:
        super().__init__('fake sqlite error')
        self.sqlite_errorcode = code


def _make_integrity_error(orig: BaseException | None) -> IntegrityError:
    return IntegrityError('INSERT INTO test_table VALUES (%s)', (1,), orig)


class TestEscapeLike:
    """BaseDataAccessLayer._escape_like LIKE 通配符转义单元测试 (防通配符注入)"""

    @pytest.mark.parametrize(
        ('keyword', 'expected'),
        [
            ('neko', 'neko'),  # 普通关键词不变
            ('', ''),  # 空字符串不变
            ('100%', r'100\%'),  # % 转义
            ('a_b', r'a\_b'),  # _ 转义
            (r'a\b', r'a\\b'),  # 反斜杠自身转义
            ('100%_off\\', r'100\%\_off\\'),  # 混合字符全部转义
            ('%_%_', r'\%\_\%\_'),  # 纯通配符全部转义
        ],
    )
    def test_escape_like(self, keyword: str, expected: str) -> None:
        from src.database.model import BaseDataAccessLayer

        assert BaseDataAccessLayer._escape_like(keyword) == expected


class TestIsUniqueConflictError:
    """is_unique_conflict_error 跨方言唯一约束冲突甄别单元测试"""

    @pytest.mark.parametrize(
        ('orig', 'expected'),
        [
            (Exception(1062, "Duplicate entry 'a' for key 'PRIMARY'"), True),  # MySQL 唯一冲突
            (Exception(1452, 'a foreign key constraint fails'), False),  # MySQL 外键冲突
            (Exception(1048, "Column 'name' cannot be null"), False),  # MySQL 非空冲突
            (_FakePostgresqlError('23505'), True),  # PostgreSQL 唯一冲突
            (_FakePostgresqlError('23503'), False),  # PostgreSQL 外键冲突
            (_FakePostgresqlError('23502'), False),  # PostgreSQL 非空冲突
            (_FakeSqliteError(2067), True),  # SQLite 唯一冲突 (CONSTRAINT_UNIQUE)
            (_FakeSqliteError(1555), True),  # SQLite 主键冲突 (CONSTRAINT_PRIMARYKEY)
            (_FakeSqliteError(787), False),  # SQLite 外键冲突 (CONSTRAINT_FOREIGNKEY)
            (_FakeSqliteError(1299), False),  # SQLite 非空冲突 (CONSTRAINT_NOTNULL)
            (None, False),  # 无原始驱动错误
        ],
    )
    def test_is_unique_conflict_error(self, orig: BaseException | None, expected: bool) -> None:
        from src.database.model import BaseDataAccessLayer

        assert BaseDataAccessLayer._is_unique_conflict_error(_make_integrity_error(orig)) is expected


class TestDatabaseSession:
    """database_session 会话上下文行为测试"""

    async def test_commit_on_normal_exit(self) -> None:
        """上下文正常退出时, 写入必须提交并对后续会话可见"""
        import random
        import string
        from datetime import datetime, timedelta

        from sqlalchemy import delete, select

        from src.database.helpers import database_session
        from src.database.schema import GlobalCacheOrm

        cache_name = f'TEST_COMMIT_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'
        cache_key = f'TEST_COMMIT_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'

        try:
            async with database_session() as session:
                session.add(GlobalCacheOrm(
                    cache_name=cache_name,
                    cache_key=cache_key,
                    cache_value='test_value',
                    expired_at=datetime.now() + timedelta(days=1),
                ))
                await session.flush()

            async with database_session() as session:
                result = await session.execute(
                    select(GlobalCacheOrm)
                    .where(GlobalCacheOrm.cache_name == cache_name)
                    .where(GlobalCacheOrm.cache_key == cache_key)
                )
                assert result.scalar_one_or_none() is not None
        finally:
            async with database_session() as session:
                await session.execute(
                    delete(GlobalCacheOrm)
                    .where(GlobalCacheOrm.cache_name == cache_name)
                    .where(GlobalCacheOrm.cache_key == cache_key)
                )

    async def test_rollback_on_exception(self) -> None:
        """上下文中发生异常时, 已 flush 的写入必须回滚, 不得提交"""
        import random
        import string
        from datetime import datetime, timedelta

        from sqlalchemy import delete, select

        from src.database.helpers import database_session
        from src.database.schema import GlobalCacheOrm

        cache_name = f'TEST_ROLLBACK_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'
        cache_key = f'TEST_ROLLBACK_{"".join(random.sample(string.ascii_letters + string.digits, k=8))}'

        try:
            async def _write_then_raise() -> None:
                async with database_session() as inner_session:
                    inner_session.add(GlobalCacheOrm(
                        cache_name=cache_name,
                        cache_key=cache_key,
                        cache_value='test_value',
                        expired_at=datetime.now() + timedelta(days=1),
                    ))
                    await inner_session.flush()
                    raise RuntimeError('expected test exception')

            with pytest.raises(RuntimeError, match='expected test exception'):
                await _write_then_raise()

            async with database_session() as session:
                result = await session.execute(
                    select(GlobalCacheOrm)
                    .where(GlobalCacheOrm.cache_name == cache_name)
                    .where(GlobalCacheOrm.cache_key == cache_key)
                )
                assert result.scalar_one_or_none() is None
        finally:
            async with database_session() as session:
                await session.execute(
                    delete(GlobalCacheOrm)
                    .where(GlobalCacheOrm.cache_name == cache_name)
                    .where(GlobalCacheOrm.cache_key == cache_key)
                )


class TestTransactionGuards:
    """基类事务守卫分支测试"""

    async def test_safe_begin_transaction_inactive_session_raises(self) -> None:
        """非活动会话上开启事务应抛出 RuntimeError"""
        from src.database.internal.global_cache import GlobalCacheDAL

        mock_session = MagicMock()
        mock_session.is_active = False
        dal = GlobalCacheDAL(session=mock_session)

        with pytest.raises(RuntimeError, match='Current session is not active'):
            async with dal.safe_begin_transaction():
                pass

    async def test_must_begin_nested_in_transaction_inactive_session_raises(self) -> None:
        """非活动会话上开启嵌套事务应抛出 RuntimeError"""
        from src.database.internal.global_cache import GlobalCacheDAL

        mock_session = MagicMock()
        mock_session.is_active = False
        dal = GlobalCacheDAL(session=mock_session)

        with pytest.raises(RuntimeError, match='Current session is not active'):
            async with dal.must_begin_nested_in_transaction():
                pass

    async def test_must_begin_nested_in_transaction_without_transaction_raises(self) -> None:
        """无外层事务时开启嵌套事务应抛出 RuntimeError"""
        from src.database.connector import get_session_factory
        from src.database.internal.global_cache import GlobalCacheDAL

        async with get_session_factory()() as session:
            dal = GlobalCacheDAL(session=session)

            with pytest.raises(RuntimeError, match='Must be executed within a session already in active transaction'):
                async with dal.must_begin_nested_in_transaction():
                    pass


class TestWriteTransactionContract:
    """DAL 写方法事务契约: 纯写方法不得自行提交, 提交统一由会话边界负责"""

    async def test_pure_write_method_not_self_commit(self) -> None:
        """纯写方法在 fresh session 上不得自行 commit, 外层 rollback 必须能撤销其写入

        回归测试: safe_begin_transaction 顶层分支若自行提交, rollback 将无法撤销, query_unique 会查到数据
        """
        from src.database.internal.global_cache import GlobalCacheDAL

        cache_name = f'TEST_NSC_NAME_{_random_string()}'
        cache_key = f'TEST_NSC_KEY_{_random_string()}'

        async with GlobalCacheDAL.create() as dal:
            await dal.add_update_exist(
                cache_name=cache_name,
                cache_key=cache_key,
                cache_value='test_value',
                expired_time=timedelta(days=1),
            )
            await dal.rollback_session()

            with pytest.raises(NoResultFound):
                await dal.query_unique(cache_name, cache_key)
