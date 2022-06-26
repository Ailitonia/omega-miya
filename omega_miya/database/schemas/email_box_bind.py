"""
@Author         : Ailitonia
@Date           : 2022/03/27 17:07
@FileName       : email_box_bind.py
@Project        : nonebot2_miya 
@Description    : EmailBoxBind Model
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
from ..model import EmailBoxBindOrm


class EmailBoxBindUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    email_box_id: int
    entity_id: int


class EmailBoxBindRequireModel(EmailBoxBindUniqueModel):
    """数据库对象变更请求必须数据模型"""
    bind_info: Optional[str]


class EmailBoxBindModel(EmailBoxBindRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class EmailBoxBindModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["EmailBoxBindModel"]


class EmailBoxBindModelListResult(DatabaseModelListResult):
    """EmailBoxBind 查询结果类"""
    result: List["EmailBoxBindModel"]


class EmailBoxBind(BaseDatabase):
    orm_model = EmailBoxBindOrm
    unique_model = EmailBoxBindUniqueModel
    require_model = EmailBoxBindRequireModel
    data_model = EmailBoxBindModel
    self_model: EmailBoxBindUniqueModel

    def __init__(self, email_box_id: int, entity_id: int):
        self.self_model = EmailBoxBindUniqueModel(email_box_id=email_box_id, entity_id=entity_id)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.email_box_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.email_box_id == self.self_model.email_box_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            order_by(self.orm_model.email_box_id)
        return stmt

    def _make_unique_self_update(self, new_model: EmailBoxBindRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.email_box_id == self.self_model.email_box_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.email_box_id == self.self_model.email_box_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, bind_info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            email_box_id=self.self_model.email_box_id,
            entity_id=self.self_model.entity_id,
            bind_info=bind_info
        ))

    async def add_upgrade_unique_self(self, bind_info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            email_box_id=self.self_model.email_box_id,
            entity_id=self.self_model.entity_id,
            bind_info=bind_info
        ))

    async def query(self) -> EmailBoxBindModelResult:
        return EmailBoxBindModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> EmailBoxBindModelListResult:
        return EmailBoxBindModelListResult.parse_obj(await cls._query_all())


__all__ = [
    'EmailBoxBind',
    'EmailBoxBindModel'
]
