"""
@Author         : Ailitonia
@Date           : 2022/02/24 23:54
@FileName       : related_entity.py
@Project        : nonebot2_miya 
@Description    : RelatedEntity model
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
from ..model import BotSelfOrm, EntityOrm, RelatedEntityOrm, AuthSettingOrm, SubscriptionOrm


RELATION_TYPE = Literal[
    'bot_group',  # Bot 所在群
    'bot_user',  # Bot 的好友/直接用户/临时会话
    'bot_guild',  # Bot 所在频道
    'guild_channel',  # 子频道
    'group_user',  # 群成员
    'guild_user'  # 频道成员
]


class RelatedEntityUniqueModel(BaseDatabaseModel):
    """数据库对象唯一性模型"""
    bot_id: int
    entity_id: int
    parent_entity_id: int
    relation_type: RELATION_TYPE


class RelatedEntityRequireModel(RelatedEntityUniqueModel):
    """数据库对象变更请求必须数据模型"""
    entity_name: str


class RelatedEntityModel(RelatedEntityRequireModel):
    """数据库对象完整模型"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class RelatedEntityModelResult(DatabaseModelResult):
    """数据库查询结果基类"""
    result: Optional["RelatedEntityModel"]


class RelatedEntityModelListResult(DatabaseModelListResult):
    """RelatedEntity 查询结果类"""
    result: List["RelatedEntityModel"]


class RelatedEntity(BaseDatabase):
    orm_model = RelatedEntityOrm
    unique_model = RelatedEntityUniqueModel
    require_model = RelatedEntityRequireModel
    data_model = RelatedEntityModel
    self_model: RelatedEntityUniqueModel

    def __init__(
            self,
            bot_id: int,
            entity_id: int,
            parent_entity_id: int,
            relation_type: RELATION_TYPE):

        self.self_model = RelatedEntityUniqueModel(
            bot_id=bot_id, entity_id=entity_id, parent_entity_id=parent_entity_id, relation_type=relation_type)

    @classmethod
    def _make_all_select(cls) -> Select:
        stmt = select(cls.orm_model).with_for_update(read=True).order_by(cls.orm_model.relation_type)
        return stmt

    def _make_unique_self_select(self) -> Select:
        stmt = select(self.orm_model).with_for_update(read=True).\
            where(self.orm_model.bot_id == self.self_model.bot_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.parent_entity_id == self.self_model.parent_entity_id).\
            where(self.orm_model.relation_type == self.self_model.relation_type).\
            order_by(self.orm_model.relation_type)
        return stmt

    def _make_unique_self_update(self, new_model: RelatedEntityRequireModel) -> Update:
        stmt = update(self.orm_model).\
            where(self.orm_model.bot_id == self.self_model.bot_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.parent_entity_id == self.self_model.parent_entity_id).\
            where(self.orm_model.relation_type == self.self_model.relation_type).\
            values(**new_model.dict()).\
            values(updated_at=datetime.now()).\
            execution_options(synchronize_session="fetch")
        return stmt

    def _make_unique_self_delete(self) -> Delete:
        stmt = delete(self.orm_model).\
            where(self.orm_model.bot_id == self.self_model.bot_id).\
            where(self.orm_model.entity_id == self.self_model.entity_id).\
            where(self.orm_model.parent_entity_id == self.self_model.parent_entity_id).\
            where(self.orm_model.relation_type == self.self_model.relation_type).\
            execution_options(synchronize_session="fetch")
        return stmt

    async def update_unique_self(self, entity_name: str) -> BoolResult:
        return await self._update_unique_self(new_model=self.require_model(
            bot_id=self.self_model.bot_id,
            entity_id=self.self_model.entity_id,
            parent_entity_id=self.self_model.parent_entity_id,
            relation_type=self.self_model.relation_type,
            entity_name=entity_name
        ))

    async def add_upgrade_unique_self(self, entity_name: str) -> BoolResult:
        return await self._add_upgrade_unique_self(new_model=self.require_model(
            bot_id=self.self_model.bot_id,
            entity_id=self.self_model.entity_id,
            parent_entity_id=self.self_model.parent_entity_id,
            relation_type=self.self_model.relation_type,
            entity_name=entity_name
        ))

    async def add_only(self, entity_name: str) -> BoolResult:
        return await self._add_only_without_upgrade_unique_self(new_model=self.require_model(
            bot_id=self.self_model.bot_id,
            entity_id=self.self_model.entity_id,
            parent_entity_id=self.self_model.parent_entity_id,
            relation_type=self.self_model.relation_type,
            entity_name=entity_name
        ))

    async def query(self) -> RelatedEntityModelResult:
        return RelatedEntityModelResult.parse_obj(await self.query_unique_self())

    @classmethod
    async def query_by_index_id(cls, id_: int) -> RelatedEntityModelResult:
        stmt = select(cls.orm_model).with_for_update(read=True).where(cls.orm_model.id == id_)
        return RelatedEntityModelResult.parse_obj(await cls._query_unique_one(stmt=stmt))

    @classmethod
    async def query_related_entity_by_index_id(cls, id_: int) -> (RelatedEntityOrm, EntityOrm, BotSelfOrm):
        """根据索引 id 查询 RelatedEntity 及其对应 Entity, BotSelf 的 Model

        :return: Tuple[RelatedEntityOrm, EntityOrm, BotSelfOrm]
        """
        stmt = select(cls.orm_model, EntityOrm, BotSelfOrm).with_for_update(read=True).\
            join(EntityOrm, onclause=cls.orm_model.entity_id == EntityOrm.id).\
            join(BotSelfOrm).\
            where(cls.orm_model.id == id_)
        return await cls._query_custom_one(stmt=stmt, scalar=False)

    @classmethod
    async def query_all(cls) -> RelatedEntityModelListResult:
        return RelatedEntityModelListResult.parse_obj(await cls._query_all())

    @classmethod
    async def query_all_by_type(cls, relation_type: str) -> RelatedEntityModelListResult:
        stmt = select(cls.orm_model).with_for_update(read=True).\
            where(cls.orm_model.relation_type == relation_type)
        return RelatedEntityModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all_by_auth_node(
            cls,
            module: str,
            plugin: str,
            node: str,
            available: int = 1,
            *,
            require_available: bool = True,
            relation_type: Optional[str] = None) -> RelatedEntityModelListResult:
        """根据权限节点查询

        :param module: 权限节点对应模块
        :param plugin: 权限节点对应插件
        :param node: 权限节点
        :param available: 启用/需求值
        :param require_available: True: 查询 available 大于等于传入参数的结果, False: 查询 available 等于传入参数的结果
        :param relation_type: None: 无限制, relation_type: 查询对应 relation_type 的结果
        """
        stmt = select(cls.orm_model).with_for_update(read=True).join(AuthSettingOrm).\
            where(AuthSettingOrm.module == module).\
            where(AuthSettingOrm.plugin == plugin).\
            where(AuthSettingOrm.node == node)

        if require_available:
            stmt = stmt.where(AuthSettingOrm.available >= available)
        else:
            stmt = stmt.where(AuthSettingOrm.available == available)

        if relation_type is not None:
            stmt = stmt.where(cls.orm_model.relation_type == relation_type)

        return RelatedEntityModelListResult.parse_obj(await cls._query_all(stmt=stmt))

    @classmethod
    async def query_all_by_subscribed_source_index_id(
            cls,
            id_: int,
            *,
            relation_type: Optional[str] = None) -> RelatedEntityModelListResult:
        """根据 SubscriptionSource 的索引 id 查询已订阅该来源的 RelatedEntity

        :param id_: SubscriptionSource 索引 id
        :param relation_type: 筛选 relation_type
        """
        stmt = select(cls.orm_model).with_for_update(read=True).\
            join(SubscriptionOrm).\
            where(SubscriptionOrm.sub_source_id == id_).order_by(cls.orm_model.entity_id)
        if relation_type is not None:
            stmt = stmt.where(cls.orm_model.relation_type == relation_type)
        return RelatedEntityModelListResult.parse_obj(await cls._query_all(stmt=stmt))


__all__ = [
    'RELATION_TYPE',
    'RelatedEntity',
    'RelatedEntityModel'
]
