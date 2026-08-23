"""
@Author         : Ailitonia
@Date           : 2026/8/23 15:10
@FileName       : test_database_init.py
@Project        : omega-miya
@Description    : src/database/helpers.py 数据库初始化钩子编排逻辑单元测试

注意: 所有 src.* 的导入一律放在测试函数体内, 原因见 tests/database/conftest.py
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Callable, Coroutine
from typing import Any
from unittest.mock import AsyncMock

import pytest


def _make_check_result(status_value: str, message: str = ''):
    """构造迁移状态检查结果 (导入延迟到运行时, 避免收集阶段触发 NoneBot 初始化依赖)"""
    from src.database.migrate import MigrationCheckResult, MigrationStatus

    return MigrationCheckResult(
        status=MigrationStatus(status_value), current_revisions=(), head='head_rev', message=message
    )


@pytest.fixture
def database_init() -> Callable[[], Coroutine[Any, Any, None]]:
    """获取 _database_init 钩子函数"""
    from src.database.helpers import _database_init

    return _database_init


@pytest.fixture
def mock_migrate(monkeypatch: pytest.MonkeyPatch) -> tuple[AsyncMock, AsyncMock]:
    """拦截 _database_init 中对 migrate 模块的调用 (检查与升级)"""
    import src.database.migrate as migrate_module

    check_mock = AsyncMock()
    upgrade_mock = AsyncMock()
    monkeypatch.setattr(migrate_module, 'check_migration_state', check_mock)
    monkeypatch.setattr(migrate_module, 'async_migrate_to_head', upgrade_mock)
    return check_mock, upgrade_mock


class TestDatabaseInit:
    """数据库初始化钩子编排逻辑测试"""

    async def test_abort_on_unsafe_check(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.return_value = _make_check_result('unstamped_database', message='test unsafe')

        with pytest.raises(SystemExit) as exc_info:
            await database_init()

        assert str(exc_info.value.code).startswith('数据库版本校验未通过')
        check_mock.assert_awaited_once()
        upgrade_mock.assert_not_awaited()

    async def test_skip_migration_when_up_to_date(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.return_value = _make_check_result('up_to_date')

        await database_init()

        check_mock.assert_awaited_once()
        upgrade_mock.assert_not_awaited()

    async def test_migrate_when_upgradable(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.side_effect = [_make_check_result('upgradable'), _make_check_result('up_to_date')]

        await database_init()

        assert check_mock.await_count == 2
        upgrade_mock.assert_awaited_once()

    async def test_migrate_when_fresh(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.side_effect = [_make_check_result('fresh'), _make_check_result('up_to_date')]

        await database_init()

        assert check_mock.await_count == 2
        upgrade_mock.assert_awaited_once()

    async def test_abort_when_post_verify_failed(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.side_effect = [_make_check_result('upgradable'), _make_check_result('upgradable')]

        with pytest.raises(SystemExit) as exc_info:
            await database_init()

        assert str(exc_info.value.code).startswith('数据库迁移后校验未通过')
        assert check_mock.await_count == 2
        upgrade_mock.assert_awaited_once()

    async def test_abort_when_migration_raised(
            self,
            database_init: Callable[[], Coroutine[Any, Any, None]],
            mock_migrate: tuple[AsyncMock, AsyncMock],
    ) -> None:
        check_mock, upgrade_mock = mock_migrate
        check_mock.return_value = _make_check_result('upgradable')
        upgrade_mock.side_effect = RuntimeError('boom')

        with pytest.raises(SystemExit) as exc_info:
            await database_init()

        assert str(exc_info.value.code).startswith('数据库初始化失败')
        check_mock.assert_awaited_once()
        upgrade_mock.assert_awaited_once()
