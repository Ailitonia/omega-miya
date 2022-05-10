"""
@Author         : Ailitonia
@Date           : 2022/02/22 17:40
@FileName       : bot_self.py
@Project        : nonebot2_miya 
@Description    : BotSelf model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import BotSelfOrm


class BotSelfUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    self_id: str


class BotSelfRequireModel(BotSelfUniqueModel):
    """数据库对象变更请求必须数据模型"""
    bot_type: str
    bot_status: int
    bot_info: Optional[str]


class BotSelfModel(BotSelfRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class BotSelfModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["BotSelfModel"]


class BotSelfModelListResult(DatabaseModelListResult):
    """BotSelf 查询结果类"""
    result: List["BotSelfModel"]


class BotSelf(BaseDatabase):
    orm_model = BotSelfOrm
    unique_model = BotSelfUniqueModel
    require_model = BotSelfRequireModel
    data_model = BotSelfModel
    self_model: BotSelfUniqueModel

    def __init__(self, self_id: str):
        self.self_model = BotSelfUniqueModel(self_id=self_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.self_id)
        return stmt

    @classmethod
    def _make_online_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.bot_status == 1).order_by(cls.orm_model.self_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.self_id == self.self_model.self_id).\
            order_by(self.orm_model.self_id)
        return stmt

    def _make_unique_self_update(self, new_model: BotSelfRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.self_id == self.self_model.self_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.self_id == self.self_model.self_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, bot_type: str, bot_status: int, bot_info: Optional[str]) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            self_id=self.self_model.self_id,
            bot_type=bot_type,
            bot_status=bot_status,
            bot_info=bot_info
        ))

    async def add_upgrade_unique_self(self, bot_type: str, bot_status: int, bot_info: Optional[str]) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            self_id=self.self_model.self_id,
            bot_type=bot_type,
            bot_status=bot_status,
            bot_info=bot_info
        ))

    async def query(self) -> BotSelfModelResult:
        return BotSelfModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_by_index_id(cls, id_: int) -> BotSelfModelResult:
        stmt = select(cls.orm_model).with_for_update(read=True).where(cls.orm_model.id == id_)
        return BotSelfModelResult.parse_obj(await cls._query_unique_one(stmt=stmt))

    @classmethod
    async def query_all_online(cls) -> BotSelfModelListResult:
        return BotSelfModelListResult.parse_obj(await cls._query_all(stmt=cls._make_online_select()))

    @classmethod
    async def query_all(cls) -> BotSelfModelListResult:
        return BotSelfModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'BotSelf',
    'BotSelfModel'
]
