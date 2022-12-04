"""
@Author         : Ailitonia
@Date           : 2022/12/02 21:46
@FileName       : bot.py
@Project        : nonebot2_miya 
@Description    : BotSelf DAL
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

from ..model import BaseDataAccessLayerModel, BotSelfOrm


@unique
class BotType(Enum):
    """Bot 类型"""
    onebot_v11: Literal['OneBot V11'] = 'OneBot V11'
    onebot_v12: Literal['OneBot V12'] = 'OneBot V12'
    telegram: Literal['Telegram'] = 'Telegram'

    @classmethod
    def verify(cls, unverified: str):
        if unverified not in [member.value for _, member in cls.__members__.items()]:
            raise ValueError(f'illegal bot_type: "{unverified}"')


class BotSelf(BaseModel):
    """BotSelf Model"""
    id: int
    self_id: str
    bot_type: BotType
    bot_status: int
    bot_info: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        extra = 'ignore'
        orm_mode = True
        allow_mutation = False


class BotSelfDAL(BaseDataAccessLayerModel):
    """BotSelf 数据库操作对象"""

    def __init__(self, session: AsyncSession):
        self.db_session = session

    @property
    def bot_type(self) -> type[BotType]:
        return deepcopy(BotType)

    async def query_unique(self, self_id: str) -> BotSelf:
        stmt = select(BotSelfOrm).where(BotSelfOrm.self_id == self_id)
        session_result = await self.db_session.execute(stmt)
        return BotSelf.from_orm(session_result.scalar_one())

    async def query_by_index_id(self, index_id: int) -> BotSelf:
        stmt = select(BotSelfOrm).where(BotSelfOrm.id == index_id)
        session_result = await self.db_session.execute(stmt)
        return BotSelf.from_orm(session_result.scalar_one())

    async def query_all(self) -> list[BotSelf]:
        stmt = select(BotSelfOrm).order_by(BotSelfOrm.self_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[BotSelf], session_result.scalars().all())

    async def query_all_online(self) -> list[BotSelf]:
        stmt = select(BotSelfOrm).where(BotSelfOrm.bot_status == 1).order_by(BotSelfOrm.self_id)
        session_result = await self.db_session.execute(stmt)
        return parse_obj_as(list[BotSelf], session_result.scalars().all())

    async def add(self, self_id: str, bot_type: str, bot_status: int, bot_info: Optional[str] = None) -> None:
        BotType.verify(bot_type)
        new_obj = BotSelfOrm(self_id=self_id, bot_type=bot_type, bot_status=bot_status,
                             bot_info=bot_info, created_at=datetime.now())
        self.db_session.add(new_obj)
        await self.db_session.flush()

    async def update(
            self,
            id_: int,
            *,
            bot_type: Optional[str] = None,
            bot_status: Optional[int] = None,
            bot_info: Optional[str] = None
    ) -> None:
        stmt = update(BotSelfOrm).where(BotSelfOrm.id == id_)
        if bot_type is not None:
            BotType.verify(bot_type)
            stmt = stmt.values(bot_type=bot_type)
        if bot_status is not None:
            stmt = stmt.values(bot_status=bot_status)
        if bot_info is not None:
            stmt = stmt.values(bot_info=bot_info)
        stmt = stmt.values(updated_at=datetime.now())
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)

    async def delete(self, id_: int) -> None:
        stmt = delete(BotSelfOrm).where(BotSelfOrm.id == id_)
        stmt.execution_options(synchronize_session="fetch")
        await self.db_session.execute(stmt)


__all__ = [
    'BotSelfDAL'
]
