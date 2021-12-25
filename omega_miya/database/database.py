import nonebot
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from .tables import Base
from .class_result import Result

driver = nonebot.get_driver()

global_config = driver.config
_DATABASE = 'mysql'
_DB_DRIVER = 'aiomysql'
_DB_USER = global_config.db_user
_DB_PASSWORD = global_config.db_password
_DB_HOST = global_config.db_host
_DB_PORT = global_config.db_port
_DB_NAME = global_config.db_name

# 格式化数据库引擎链接
__DB_ENGINE = f'{_DATABASE}+{_DB_DRIVER}://{_DB_USER}:{quote(str(_DB_PASSWORD))}@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}'


# 创建数据库连接
try:
    engine = create_async_engine(
        __DB_ENGINE, encoding='utf8',
        connect_args={"use_unicode": True, "charset": "utf8mb4"},
        pool_recycle=3600, pool_pre_ping=True, echo=False
    )
except Exception as e:
    import sys
    nonebot.logger.opt(colors=True).critical(f'<r>创建数据库连接失败</r>, error: {repr(e)}')
    sys.exit(f'创建数据库连接失败, {e}')


# 初始化化数据库
@driver.on_startup
async def database_init():
    nonebot.logger.opt(colors=True).info(f'<lc>正在初始化数据库......</lc>')
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
        nonebot.logger.opt(colors=True).success(f'<lg>数据库初始化已完成.</lg>')
    except Exception as e_:
        import sys
        nonebot.logger.opt(colors=True).critical(f'<r>数据库初始化失败</r>, error: {repr(e_)}')
        sys.exit(f'数据库初始化失败, {e_}')


class BaseDB(object):
    def __init__(self):
        # expire_on_commit=False will prevent attributes from being expired
        # after commit.
        self.__async_session = sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )

    def get_async_session(self):
        # 创建DBSession对象
        return self.__async_session


class DBTable(object):
    """
    已弃用, 保留相关代码仅供参考
    任何情况下请直接调用 model 中相关类, 不要使用本类构造实例
    """
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

    async def list_col(self, col_name) -> Result.ListResult:
        res = []
        if not self.__table:
            result = Result.ListResult(error=True, info='Table not exist', result=res)
        else:
            async_session = BaseDB().get_async_session()
            async with async_session() as session:
                async with session.begin():
                    try:
                        col = getattr(self.__table, col_name)
                        session_result = await session.execute(select(col))
                        for item in session_result.scalars().all():
                            res.append(item)
                        result = Result.ListResult(error=False, info='Success', result=res)
                    except Exception as e_:
                        result = Result.ListResult(error=True, info=repr(e_), result=res)
        return result

    async def list_col_with_condition(self, col_name, condition_col_name, condition) -> Result.ListResult:
        res = []
        if not self.__table:
            result = Result.ListResult(error=True, info='Table not exist', result=res)
        else:
            async_session = BaseDB().get_async_session()
            async with async_session() as session:
                async with session.begin():
                    try:
                        col = getattr(self.__table, col_name)
                        condition_col = getattr(self.__table, condition_col_name)
                        session_result = await session.execute(select(col).where(condition_col == condition))
                        for item in session_result.scalars().all():
                            res.append(item)
                        result = Result.ListResult(error=False, info='Success', result=res)
                    except Exception as e_:
                        result = Result.ListResult(error=True, info=repr(e_), result=res)
        return result


__all__ = [
    'BaseDB'
]
