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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from urllib.parse import quote

from .config import database_config


try:
    # 格式化数据库引擎链接
    __db_engine = f'{database_config.database}+{database_config.db_driver.value}://{database_config.db_user}' \
                 f':{quote(str(database_config.db_password))}@{database_config.db_host}:{database_config.db_port}' \
                 f'/{database_config.db_name}'

    # 创建数据库连接
    engine = create_async_engine(
        __db_engine, encoding='utf8', connect_args={"use_unicode": True, "charset": "utf8mb4"},
        future=True,  # 使用 2.0 API，向后兼容
        pool_recycle=3600, pool_pre_ping=True, echo=False
    )

    # 创建异步 session
    # expire_on_commit=False will prevent attributes from being expired after commit.
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
except Exception as e:
    import sys
    logger.opt(colors=True).critical(f'<r>创建数据库连接失败</r>, 错误信息: {e}')
    sys.exit(f'创建数据库连接失败, {e}')


__all__ = [
    'async_session',
    'engine'
]
