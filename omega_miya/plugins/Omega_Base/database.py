import nonebot
from typing import Union
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.session import Session
from .tables import *


class NBdb(object):
    def __init__(self):
        global_config = nonebot.get_driver().config
        self.__DATABASE = global_config.database
        self.__DB_DRIVER = global_config.db_driver
        self.__DB_USER = global_config.db_user
        self.__DB_PASSWORD = global_config.db_password
        self.__DB_HOST = global_config.db_host
        self.__DB_PORT = global_config.db_port
        self.__DB_NAME = global_config.db_name

        # 格式化数据库引擎链接
        self.__DB_ENGINE = f'{self.__DATABASE}+{self.__DB_DRIVER}://' \
                           f'{self.__DB_USER}:{self.__DB_PASSWORD}@{self.__DB_HOST}:{self.__DB_PORT}/{self.__DB_NAME}'

        self.__session = Session

        # 初始化数据库连接
        self.__engine = create_engine(self.__DB_ENGINE, encoding='utf8',
                                      connect_args={"use_unicode": True, "charset": "utf8mb4"},
                                      pool_recycle=3600, pool_pre_ping=True)
        # 初始化数据库结构
        Base.metadata.create_all(self.__engine)

    def get_session(self):
        # 创建DBSession对象
        self.__session = sessionmaker()
        self.__session.configure(bind=self.__engine)
        return scoped_session(self.__session)()


class DBResult(object):
    def __init__(self, error: bool, info: str, result: Union[int, str, list, dict]):
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

    def list_col(self, col_name) -> DBResult:
        res = []
        if not self.__table:
            result = DBResult(error=True, info='Table not exist', result=res)
        else:
            session = NBdb().get_session()
            try:
                col = getattr(self.__table, col_name)
                for item in session.query(col).all():
                    res.append(item)
                result = DBResult(error=False, info='Success', result=res)
            except Exception as e:
                result = DBResult(error=True, info=str(e), result=res)
            finally:
                session.close()
        return result
