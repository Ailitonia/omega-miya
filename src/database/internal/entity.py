"""
@Author         : Ailitonia
@Date           : 2022/12/03 15:24
@FileName       : entity.py
@Project        : nonebot2_miya 
@Description    : Entity DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from copy import deepcopy
from datetime import datetime
from enum import Enum, unique
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import Literal, Optional

from pydantic import BaseModel, parse_obj_as

from ..model import BaseDataAccessLayerModel, EntityOrm


@unique
class EntityType(Enum):
    """实体对象类型"""
    qq_user: Literal['qq_user'] = 'qq_user'  # QQ 用户
    qq_group: Literal['qq_group'] = 'qq_group'  # QQ 群组
    qq_guild: Literal['qq_guild'] = 'qq_guild'  # QQ 频道
    qq_guild_user: Literal['qq_guild_user'] = 'qq_guild_user'  # QQ 频道系统内用户
    qq_guild_channel: Literal['qq_guild_channel'] = 'qq_guild_channel'  # QQ 频道子频道
    telegram_user: Literal['telegram_user'] = 'telegram_user'  # Telegram 用户
    telegram_group: Literal['telegram_group'] = 'telegram_group'  # Telegram 群组
    telegram_channel: Literal['telegram_channel'] = 'telegram_channel'  # Telegram 频道

    @classmethod
    def verify(cls, unverified: str):
        if unverified not in [member.value for _, member in cls.__members__.items()]:
            raise ValueError(f'illegal entity_type: "{unverified}"')


class Entity(BaseModel):
    """实体对象 Model"""
    id: int
    bot_index_id: int  # 所属 Bot 索引 ID
    entity_id: str  # 本身的实体 ID
    entity_type: EntityType  # 实体对象类型
    parent_id: str  # 父实体 ID
    entity_name: str  # 实体名称
    entity_info: Optional[str]  # 实体描述信息
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class EntityDAL(BaseDataAccessLayerModel):
    """实体对象 数据库操作对象"""

    def __init__(self, session: AsyncSession):
        self.db_session = session

    @property
    def entity_type(self) -> type[EntityType]:
        return deepcopy(EntityType)

    async def query_unique(
            self,
            bot_index_id: int,
            entity_id: str,
            entity_type: str,
            parent_id: str
    ) -> Entity:
        EntityType.verify(entity_type)
        stmt = select(EntityOrm).\
            where(EntityOrm.bot_index_id == bot_index_id).\
            where(EntityOrm.entity_id == entity_id).\
            where(EntityOrm.entity_type == entity_type).\
            where(EntityOrm.parent_id == parent_id)
        session_result = await self.db_session.execute(stmt)
        return Entity.from_orm(session_result.scalar_one())

    async def query_with_index_id(self, index_id: int) -> Entity:
        stmt = select(EntityOrm).where(EntityOrm.id == index_id)
        session_result = await self.db_session.execute(stmt)
        return Entity.from_orm(session_result.scalar_one())

    async def query_all(self) -> list[Entity]:
        stmt = select(EntityOrm).order_by(EntityOrm.entity_type)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[Entity], session_result.scalars().all())

    async def add(
            self,
            bot_index_id: int,
            entity_id: str,
            entity_type: str,
            parent_id: str,
            entity_name: str,
            entity_info: Optional[str] = None
    ) -> None:
        EntityType.verify(entity_type)
        new_obj = EntityOrm(bot_index_id=bot_index_id, entity_id=entity_id, entity_type=entity_type,
                            parent_id=parent_id, entity_name=entity_name,
                            entity_info=entity_info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            bot_index_id: Optional[int] = None,
            entity_id: Optional[str] = None,
            entity_type: Optional[str] = None,
            parent_id: Optional[str] = None,
            entity_name: Optional[str] = None,
            entity_info: Optional[str] = None
    ) -> None:
        stmt = update(EntityOrm).where(EntityOrm.id == id_)
        if bot_index_id is not None:
            stmt = stmt.values(bot_index_id=bot_index_id)
        if entity_id is not None:
            stmt = stmt.values(entity_id=entity_id)
        if entity_type is not None:
            EntityType.verify(entity_type)
            stmt = stmt.values(entity_type=entity_type)
        if parent_id is not None:
            stmt = stmt.values(parent_id=parent_id)
        if entity_name is not None:
            stmt = stmt.values(entity_name=entity_name)
        if entity_info is not None:
            stmt = stmt.values(entity_info=entity_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(EntityOrm).where(EntityOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'EntityDAL'
]
