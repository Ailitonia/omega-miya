"""
@Author         : Ailitonia
@Date           : 2022/02/21 10:58
@FileName       : connector.py
@Project        : nonebot2_miya 
@Description    : database connector
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import get_driver, logger
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from .model import Base
from .config import database_config


# 格式化数据库引擎链接
_db_engine = f'{database_config.database}+{database_config.db_driver.value}://{database_config.db_user}' \
             f':{quote(str(database_config.db_password))}@{database_config.db_host}:{database_config.db_port}' \
             f'/{database_config.db_name}'


# 创建数据库连接
try:
    engine = create_async_engine(
        _db_engine, encoding='utf8', connect_args={"use_unicode": True, "charset": "utf8mb4"},
        future=True,  # 使用 2.0 API，向后兼容
        pool_recycle=3600, pool_pre_ping=True, echo=False
    )
except Exception as e:
    import sys
    logger.opt(colors=True).critical(f'<r>创建数据库连接失败</r>, error: {e}')
    sys.exit(f'创建数据库连接失败, {e}')


# 初始化化数据库
@get_driver().on_startup
async def database_init():
    logger.opt(colors=True).info(f'<lc>正在初始化数据库......</lc>')
    try:
        # 初始化数据库结构
        # conn is an instance of AsyncConnection
        async with engine.begin() as conn:
            # to support SQLAlchemy DDL methods as well as legacy functions, the
            # AsyncConnection.run_sync() awaitable method will pass a "sync"
            # version of the AsyncConnection object to any synchronous method,
            # where synchronous IO calls will be transparently translated for
            # await.
            await conn.run_sync(Base.metadata.create_all)
        logger.opt(colors=True).success(f'<lg>数据库初始化已完成.</lg>')
    except Exception as _e:
        import sys
        logger.opt(colors=True).critical(f'<r>数据库初始化失败</r>, 错误信息: {_e}')
        sys.exit(f'数据库初始化失败, {_e}')


# 导出数据库 session 对象
class _BaseDatabase(object):
    def __init__(self):
        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        self._async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

    def get_async_session(self):
        # 导出 Session 对象
        return self._async_session


PersistentDatabase = _BaseDatabase()


__all__ = [
    'PersistentDatabase'
]
