"""
@Author         : Ailitonia
@Date           : 2022/03/27 16:47
@FileName       : email_box.py
@Project        : nonebot2_miya 
@Description    : EmailBox Model
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
from ..model import EmailBoxOrm, EmailBoxBindOrm


class EmailBoxUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    address: str


class EmailBoxRequireModel(EmailBoxUniqueModel):
    """数据库对象变更请求必须数据模型"""
    server_host: str
    protocol: str
    port: int
    password: str


class EmailBoxModel(EmailBoxRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class EmailBoxModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["EmailBoxModel"]


class EmailBoxModelListResult(DatabaseModelListResult):
    """EmailBox 查询结果类"""
    result: List["EmailBoxModel"]


class EmailBox(BaseDatabase):
    orm_model = EmailBoxOrm
    unique_model = EmailBoxUniqueModel
    require_model = EmailBoxRequireModel
    data_model = EmailBoxModel
    self_model: EmailBoxUniqueModel

    def __init__(self, address: str):
        self.self_model = EmailBoxUniqueModel(address=address)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.address)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.address == self.self_model.address).\
            order_by(self.orm_model.address)
        return stmt

    def _make_unique_self_update(self, new_model: EmailBoxRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.address == self.self_model.address).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.address == self.self_model.address).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(
            self,
            server_host: str,
            password: str,
            *,
            protocol: str = 'imap',
            port: int = 993
    ) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            address=self.self_model.address,
            server_host=server_host,
            protocol=protocol,
            port=port,
            password=password
        ))

    async def add_upgrade_unique_self(
            self,
            server_host: str,
            password: str,
            *,
            protocol: str = 'imap',
            port: int = 993
    ) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            address=self.self_model.address,
            server_host=server_host,
            protocol=protocol,
            port=port,
            password=password
        ))

    async def query(self) -> EmailBoxModelResult:
        return EmailBoxModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_all(cls) -> EmailBoxModelListResult:
        return EmailBoxModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_bound_entity_index_id(cls, id_: int) -> EmailBoxModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).join(EmailBoxBindOrm).\
            where(EmailBoxBindOrm.entity_id == id_).\
            order_by(cls.orm_model.id)
        return EmailBoxModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'EmailBox',
    'EmailBoxModel'
]
