"""
@Author         : Ailitonia
@Date           : 2022/03/23 22:13
@FileName       : sign_in.py
@Project        : nonebot2_miya 
@Description    : SignIn model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List, Optional
from datetime import date, datetime
from sqlalchemy import update, delete, desc
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import SignInOrm


class SignInUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    entity_id: int
    sign_in_date: date


class SignInRequireModel(SignInUniqueModel):
    """数据库对象变更请求必须数据模型"""
    sign_in_info: Optional[str]


class SignInModel(SignInRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class SignInModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["SignInModel"]


class SignInModelListResult(DatabaseModelListResult):
    """SignIn 查询结果类"""
    result: List["SignInModel"]


class SignIn(BaseDatabase):
    orm_model = SignInOrm
    unique_model = SignInUniqueModel
    require_model = SignInRequireModel
    data_model = SignInModel
    self_model: SignInUniqueModel

    def __init__(self, entity_id: int, sign_in_date: date):
        self.self_model = SignInUniqueModel(entity_id=entity_id, sign_in_date=sign_in_date)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.entity_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.sign_in_date == self.self_model.sign_in_date).\
            order_by(self.orm_model.entity_id)
        return stmt

    def _make_unique_self_update(self, new_model: SignInRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.sign_in_date == self.self_model.sign_in_date).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.sign_in_date == self.self_model.sign_in_date).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, sign_in_info: Optional[str]) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            sign_in_date=self.self_model.sign_in_date,
            sign_in_info=sign_in_info
        ))

    async def add_upgrade_unique_self(self, sign_in_info: Optional[str]) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            sign_in_date=self.self_model.sign_in_date,
            sign_in_info=sign_in_info
        ))

    async def query(self) -> SignInModelResult:
        return SignInModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> SignInModelListResult:
        return SignInModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_entity_all_signin_date(cls, entity_id: int) -> List[date]:
        stmt = select(cls.orm_model.sign_in_date).with_for_update(read=True).\
            where(cls.orm_model.entity_id == entity_id).\
            order_by(desc(cls.orm_model.sign_in_date))
        return await cls._query_custom_all(stmt=stmt)


__all__ = [
    'SignIn',
    'SignInModel'
]
