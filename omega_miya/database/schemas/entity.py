"""
@Author         : Ailitonia
@Date           : 2022/02/24 22:47
@FileName       : entity.py
@Project        : nonebot2_miya 
@Description    : Entity model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, List, Optional
from datetime import datetime
from sqlalchemy import update, delete
from sqlalchemy.future import select
from omega_miya.result import BoolResult
from .base_model import (BaseDatabaseModel, BaseDatabase, Select, Update, Delete,
                         DatabaseModelResult, DatabaseModelListResult)
from ..model import EntityOrm, RelatedEntityOrm, SubscriptionOrm


ENTITY_TYPE = Literal[
    'bot_self',  # Bot 自身(特殊, 是所有对应群组、好友、频道的父实体)
    'guild_bot_self',  # 频道系统内 Bot 自身
    'qq_guild_user',  # 频道系统内用户
    'qq_user',  # 用户
    'qq_group',  # 群组
    'qq_guild',  # 频道
    'qq_channel'  # 子频道
]


class EntityUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    entity_id: str
    entity_type: ENTITY_TYPE


class EntityRequireModel(EntityUniqueModel):
    """数据库对象变更请求必须数据模型"""
    entity_name: str
    entity_info: Optional[str]


class EntityModel(EntityRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class EntityModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["EntityModel"]


class EntityModelListResult(DatabaseModelListResult):
    """Entity 查询结果类"""
    result: List["EntityModel"]


class Entity(BaseDatabase):
    orm_model = EntityOrm
    unique_model = EntityUniqueModel
    require_model = EntityRequireModel
    data_model = EntityModel
    self_model: EntityUniqueModel

    def __init__(self, entity_id: str, entity_type: ENTITY_TYPE):
        self.self_model = EntityUniqueModel(entity_id=entity_id, entity_type=entity_type)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.entity_id)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.entity_type == self.self_model.entity_type).\
            order_by(self.orm_model.entity_id)
        return stmt

    def _make_unique_self_update(self, new_model: EntityRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.entity_type == self.self_model.entity_type).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.entity_type == self.self_model.entity_type).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, entity_name: str, entity_info: Optional[str] = None) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            entity_type=self.self_model.entity_type,
            entity_name=entity_name,
            entity_info=entity_info
        ))

    async def add_upgrade_unique_self(self, entity_name: str, entity_info: Optional[str] = None) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            entity_type=self.self_model.entity_type,
            entity_name=entity_name,
            entity_info=entity_info
        ))

    async def add_only(self, entity_name: str, entity_info: Optional[str] = None) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            entity_id=self.self_model.entity_id,
            entity_type=self.self_model.entity_type,
            entity_name=entity_name,
            entity_info=entity_info
        ))

    async def query(self) -> EntityModelResult:
        return EntityModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_by_index_id(cls, id_: int) -> EntityModelResult:
        stmt = select(cls.orm_model).with_for_update(read=True).where(cls.orm_model.id == id_)
        return EntityModelResult.parse_obj(await cls._query_unique_one(stmt=stmt))

    @classmethod
    async def query_all(cls) -> EntityModelListResult:
        return EntityModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_subscribed_source_index_id(
            cls,
            id_: int,
            *,
            entity_type: Optional[str] = None) -> EntityModelListResult:
        """根据 SubscriptionSource 的索引 id 查询已订阅该来源的 Entity

        :param id_: SubscriptionSource 索引 id
        :param entity_type: 筛选 entity_type
        """
        stmt = select(cls.orm_model).with_for_update(read=True).\
            join(RelatedEntityOrm, onclause=cls.orm_model.id == RelatedEntityOrm.entity_id).\
            join(SubscriptionOrm, onclause=RelatedEntityOrm.id == SubscriptionOrm.entity_id).\
            where(SubscriptionOrm.sub_source_id == id_).order_by(cls.orm_model.entity_id)
        if entity_type is not None:
            stmt = stmt.where(cls.orm_model.entity_type == entity_type)
        return EntityModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'ENTITY_TYPE',
    'Entity',
    'EntityModel'
]
