"""
@Author         : Ailitonia
@Date           : 2022/03/27 12:58
@FileName       : bili_dynamic.py
@Project        : nonebot2_miya 
@Description    : BiliDynamic Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import datetime
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import BiliDynamicOrm


class BiliDynamicUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    dynamic_id: int


class BiliDynamicRequireModel(BiliDynamicUniqueModel):
    """数据库对象变更请求必须数据模型"""
    dynamic_type: int
    uid: int
    content: str


class BiliDynamicModel(BiliDynamicRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class BiliDynamicModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["BiliDynamicModel"]


class BiliDynamicModelListResult(DatabaseModelListResult):
    """BiliDynamic 查询结果类"""
    result: List["BiliDynamicModel"]


class BiliDynamic(BaseDatabase):
    orm_model = BiliDynamicOrm
    unique_model = BiliDynamicUniqueModel
    require_model = BiliDynamicRequireModel
    data_model = BiliDynamicModel
    self_model: BiliDynamicUniqueModel

    def __init__(self, dynamic_id: int):
        self.self_model = BiliDynamicUniqueModel(dynamic_id=dynamic_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(desc(cls.orm_model.dynamic_id))
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).\
            where(self.orm_model.dynamic_id == self.self_model.dynamic_id).\
            order_by(desc(self.orm_model.dynamic_id))
        return stmt

    def _make_unique_self_update(self, new_model: BiliDynamicRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.dynamic_id == self.self_model.dynamic_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.dynamic_id == self.self_model.dynamic_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, dynamic_type: int, uid: int, content: str) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            dynamic_id=self.self_model.dynamic_id,
            dynamic_type=dynamic_type,
            uid=uid,
            content=content
        ))

    async def add_upgrade_unique_self(self, dynamic_type: int, uid: int, content: str) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            dynamic_id=self.self_model.dynamic_id,
            dynamic_type=dynamic_type,
            uid=uid,
            content=content
        ))

    async def add_only(self, dynamic_type: int, uid: int, content: str) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            dynamic_id=self.self_model.dynamic_id,
            dynamic_type=dynamic_type,
            uid=uid,
            content=content
        ))

    async def query(self) -> BiliDynamicModelResult:
        return BiliDynamicModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> BiliDynamicModelListResult:
        return BiliDynamicModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_uid(cls, uid: int) -> BiliDynamicModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.uid == uid).order_by(cls.orm_model.dynamic_id)
        return BiliDynamicModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'BiliDynamic'
]
