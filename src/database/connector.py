"""
@Author         : Ailitonia
@Date           : 2022/12/01 20:20
@FileName       : connector.py
@Project        : nonebot2_miya 
@Description    : omega database connector
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from nonebot import logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import database_config


try:
    # 创建数据库连接
    engine = create_async_engine(
        database_config.connector.url,
        future=True,  # 使用 2.0 API，向后兼容
        pool_recycle=3600, pool_pre_ping=True, echo=False,  # 连接池配置
        **database_config.connector.connect_args  # 数据库连接参数
    )
    logger.opt(colors=True).info(f'<lc>Database</lc> | 已配置 <lg>{database_config.database}</lg> 数据库连接')

    # expire_on_commit=False will prevent attributes from being expired after commit.
    async_session_factory = async_sessionmaker(
        engine, class_=AsyncSession, autoflush=True, expire_on_commit=False
    )
except Exception as e:
    import sys
    logger.opt(colors=True).critical(f'<r>创建数据库连接失败</r>, 错误信息: {e}')
    sys.exit(f'创建数据库连接失败, {e}')


__all__ = [
    'async_session_factory',
    'engine'
]
