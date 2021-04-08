import nonebot
from typing import Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from .tables import Base

global_config = nonebot.get_driver().config
__DATABASE = 'mysql'
__DB_DRIVER = 'aiomysql'
__DB_USER = global_config.db_user
__DB_PASSWORD = global_config.db_password
__DB_HOST = global_config.db_host
__DB_PORT = global_config.db_port
__DB_NAME = global_config.db_name

# 格式化数据库引擎链接
__DB_ENGINE = f'{__DATABASE}+{__DB_DRIVER}://{__DB_USER}:{__DB_PASSWORD}@{__DB_HOST}:{__DB_PORT}/{__DB_NAME}'


# 创建数据库连接
engine = create_async_engine(__DB_ENGINE, encoding='utf8',
                             connect_args={"use_unicode": True, "charset": "utf8mb4"},
                             pool_recycle=3600, pool_pre_ping=True, echo=False)


async def database_init():
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

    except Exception as e:
        import sys
        nonebot.logger.critical(f'数据库初始化失败, error: {repr(e)}')
        sys.exit('数据库初始化失败')


# 初始化化数据库
nonebot.get_driver().on_startup(database_init)


class NBdb(object):
    def __init__(self):
        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        self.__async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

    def get_async_session(self):
        # 创建DBSession对象
        return self.__async_session


class DBResult(object):
    def __init__(self, error: bool, info: str, result: Union[int, str, list, set, dict]):
        self.error = error
        self.info = info
        self.result = result

    def success(self) -> bool:
        if not self.error:
            return True
        else:
            return False

    def __repr__(self):
        return f'<DBResult(error={self.error}, info={self.info}, result={self.result})>'


class DBTable(object):
    def __init__(self, table_name):
        self.__tables = Base
        self.table_name = table_name
        self.__table = self.__get_table()

    def __get_table(self):
        for subclass in self.__tables.__subclasses__():
            if self.table_name == subclass.__name__:
                return subclass
        else:
            return None

    async def list_col(self, col_name) -> DBResult:
        res = []
        if not self.__table:
            result = DBResult(error=True, info='Table not exist', result=res)
        else:
            async_session = NBdb().get_async_session()
            async with async_session() as session:
                async with session.begin():
                    try:
                        col = getattr(self.__table, col_name)
                        session_result = await session.execute(select(col))
                        for item in session_result.scalars().all():
                            res.append(item)
                        result = DBResult(error=False, info='Success', result=res)
                    except Exception as e:
                        result = DBResult(error=True, info=repr(e), result=res)
        return result

    async def list_col_with_condition(self, col_name, condition_col_name, condition) -> DBResult:
        res = []
        if not self.__table:
            result = DBResult(error=True, info='Table not exist', result=res)
        else:
            async_session = NBdb().get_async_session()
            async with async_session() as session:
                async with session.begin():
                    try:
                        col = getattr(self.__table, col_name)
                        condition_col = getattr(self.__table, condition_col_name)
                        session_result = await session.execute(select(col).where(condition_col == condition))
                        for item in session_result.scalars().all():
                            res.append(item)
                        result = DBResult(error=False, info='Success', result=res)
                    except Exception as e:
                        result = DBResult(error=True, info=repr(e), result=res)
        return result
