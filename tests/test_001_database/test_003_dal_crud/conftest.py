"""
@Author         : Ailitonia
@Date           : 2026/09/03 01:10
@FileName       : conftest.py
@Project        : omega-miya
@Description    : DAL CRUD 测试 fixtures, 确保测试数据库结构处于最新版本

注意: 所有 src.* 的导入一律放在 fixture 函数体内, 原因见 tests/test_001_database/conftest.py
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import pytest


@pytest.fixture(scope='session', autouse=True)
async def ensure_database_schema_ready(after_nonebot_init: None) -> None:
    """确保测试数据库结构已迁移到最新版本

    使本目录的 DAL CRUD 测试可以脱离 test_001 迁移测试单独运行 (空库/落后库自动迁移到 head),
    数据库不可达或迁移状态不安全时跳过本目录全部测试而非批量失败
    """
    from src.database.migrate import MigrationStatus, async_migrate_to_head, check_migration_state

    try:
        check_result = await check_migration_state()
    except Exception as e:
        pytest.skip(f'无法连接测试数据库, 已跳过 DAL CRUD 测试: {e}')

    if check_result.status is MigrationStatus.UP_TO_DATE:
        return

    if not check_result.is_safe:
        pytest.skip(f'测试数据库迁移状态不安全, 已跳过 DAL CRUD 测试: {check_result.message}')

    await async_migrate_to_head()
