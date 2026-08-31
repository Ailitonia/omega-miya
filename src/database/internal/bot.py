"""
@Author         : Ailitonia
@Date           : 2022/12/02 21:46
@FileName       : bot.py
@Project        : nonebot2_miya
@Description    : BotSelf DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from enum import StrEnum, unique

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import BotSelfOrm


@unique
class BotType(StrEnum):
    """Bot 类型"""
    console = 'Console'
    onebot_v11 = 'OneBot V11'
    onebot_v12 = 'OneBot V12'
    qq = 'QQ'
    telegram = 'Telegram'

    @classmethod
    def get_supported_adapter_names(cls) -> set[str]:
        return {member.value for _, member in cls.__members__.items()}


class BotSelf(BaseDataOutModel):
    """Bot 自身数据"""
    id: int
    bot_type: BotType
    self_id: str
    bot_status: int
    bot_info: str | None
    created_at: datetime | None
    updated_at: datetime | None

    def __str__(self) -> str:
        return f'{self.bot_type.value} Bot(id={self.id}, self_id={self.self_id}, status={self.bot_status})'


class BotSelfDAL(BaseDataAccessLayer[BotSelfOrm, BotSelf]):
    """Bot 自身"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(BotSelfOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(BotSelfOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            bot_type: str,
            self_id: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> BotSelfOrm:
        stmt = (select(BotSelfOrm)
                .where(BotSelfOrm.bot_type == bot_type)
                .where(BotSelfOrm.self_id == self_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def _select_from_index_id(
            self,
            index_id: int,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> BotSelfOrm:
        stmt = select(BotSelfOrm).where(BotSelfOrm.id == index_id)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            bot_type: str | None,
            self_id: str | None,
            index_id: int | None,
            *,
            populate_existing: bool = False,
    ) -> BotSelf:
        if (bot_type is None) and (self_id is None) and (index_id is None):
            raise ValueError('bot_type self_id and index_id parameters can not all be None')
        elif index_id is not None:
            item = await self._select_from_index_id(index_id, populate_existing=populate_existing)
        elif (bot_type is not None) and (self_id is not None):
            item = await self._select_unique(bot_type, self_id, populate_existing=populate_existing)
        else:
            raise ValueError('bot_type and self_id must both be provided when index_id is None')

        return BotSelf.model_validate(item)

    async def query_all(
            self,
            bot_type: str | None = None,
            *,
            populate_existing: bool = False,
    ) -> list[BotSelf]:
        stmt = select(BotSelfOrm).order_by(BotSelfOrm.self_id)

        if bot_type is not None:
            stmt = stmt.where(BotSelfOrm.bot_type == bot_type)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[BotSelf], (await self.db_session.execute(stmt)).scalars().all())

    async def query_all_online(
            self,
            bot_type: str | None = None,
            *,
            populate_existing: bool = False,
    ) -> list[BotSelf]:
        stmt = select(BotSelfOrm).where(BotSelfOrm.bot_status == 1).order_by(BotSelfOrm.self_id)

        if bot_type is not None:
            stmt = stmt.where(BotSelfOrm.bot_type == bot_type)

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[BotSelf], (await self.db_session.execute(stmt)).scalars().all())

    async def add(
            self,
            bot_type: str,
            self_id: str,
            bot_status: int,
            bot_info: str | None = None,
    ) -> BotSelf:
        """向数据库插入新行, 不校验唯一性

        尽量保证插入的是新数据时才使用, 冲突直接抛出异常
        """
        new_obj = BotSelfOrm(
            bot_type=BotType(bot_type),
            self_id=self_id,
            bot_status=bot_status,
            bot_info=bot_info,
        )
        self.db_session.add(new_obj)
        await self.db_session.flush()
        await self.db_session.refresh(new_obj)
        return BotSelf.model_validate(new_obj)

    async def add_update_exist(
            self,
            bot_type: str,
            self_id: str,
            bot_status: int,
            bot_info: str | None = None,
    ) -> BotSelf:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """
        new_obj = BotSelfOrm(
            bot_type=BotType(bot_type),
            self_id=self_id,
            bot_status=bot_status,
            bot_info=bot_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
            await session.refresh(new_obj)
            return BotSelf.model_validate(new_obj)
        except IntegrityError:
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    bot_type,
                    self_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.bot_status = bot_status
                exist_obj.bot_info = bot_info
                await session.flush()
            await session.refresh(exist_obj)
            return BotSelf.model_validate(exist_obj)

    async def delete(self, bot_type: str, self_id: str) -> None:
        stmt = delete(BotSelfOrm).where(BotSelfOrm.bot_type == bot_type).where(BotSelfOrm.self_id == self_id)
        await self.db_session.execute(stmt)


__all__ = [
    'BotSelf',
    'BotSelfDAL',
    'BotType',
]
