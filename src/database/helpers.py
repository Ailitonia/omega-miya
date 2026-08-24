"""
@Author         : Ailitonia
@Date           : 2022/12/02 19:28
@FileName       : utils.py
@Project        : nonebot2_miya
@Description    : Database utils
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from nonebot import get_driver, logger
from nonebot.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .connector import get_engine, get_scoped_session_factory


@get_driver().on_startup
async def _database_init():
    """初始化数据库, 执行表结构检查及迁移"""
    import sys
    from .migrate import MigrationStatus, async_migrate_to_head, check_migration_state

    logger.opt(colors=True).info('<lc>Database</lc> | <ly>正在初始化数据库</ly>')
    try:
        # 迁移前置检查: 校验数据库版本状态, 确认可以安全执行自动迁移
        check_result = await check_migration_state()
        if not check_result.is_safe:
            logger.opt(colors=True).critical(
                f'<lc>Database</lc> | <r>数据库版本校验未通过, 已中止启动</r>\n{check_result.message}'
            )
            sys.exit(f'数据库版本校验未通过, {check_result.message}')

        if check_result.status is MigrationStatus.UP_TO_DATE:
            logger.opt(colors=True).success('<lc>Database</lc> | <lg>数据库已是最新版本, 无需迁移</lg>')
            return

        if check_result.status is MigrationStatus.UPGRADABLE:
            logger.opt(colors=True).info(f'<lc>Database</lc> | <ly>{check_result.message}</ly>')

        # 执行自动迁移
        await async_migrate_to_head()

        # 迁移后校验: 确认数据库已升级到最新版本
        verify_result = await check_migration_state()
        if verify_result.status is not MigrationStatus.UP_TO_DATE:
            logger.opt(colors=True).critical(
                f'<lc>Database</lc> | <r>数据库迁移后校验未通过</r>, 当前状态: {verify_result.status}'
            )
            sys.exit(f'数据库迁移后校验未通过, {verify_result.message}')

        logger.opt(colors=True).success('<lc>Database</lc> | <lg>数据库初始化已完成</lg>')
    except SystemExit:
        raise
    except Exception as e:
        logger.opt(colors=True).critical(f'<lc>Database</lc> | <r>数据库初始化失败</r>, 错误信息: {e}')
        sys.exit(f'数据库初始化失败, {e}')


@get_driver().on_shutdown
async def __database_dispose():
    """断开数据库链接 (for AsyncEngine created in function scope, close and clean-up pooled connections)"""
    await get_engine().dispose()
    logger.opt(colors=True).info('<lc>Database</lc> | <ly>已断开数据库连接</ly>')


@asynccontextmanager
async def begin_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库 AsyncSession"""
    scoped_session_factory = get_scoped_session_factory()
    try:
        async with scoped_session_factory() as session:
            try:
                yield session
                await session.commit()
            except:
                await session.rollback()
                raise
    finally:
        await scoped_session_factory.remove()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库 AsyncSession 生成器依赖 (Dependence for database AsyncSession)"""
    async with begin_db_session() as session:
        yield session


type DATABASE_SESSION = Annotated[AsyncSession, Depends(get_db_session)]
"""子依赖: 获取数据库 AsyncSession"""


__all__ = [
    'DATABASE_SESSION',
    'begin_db_session',
    'get_db_session',
]
