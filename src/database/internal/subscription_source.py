"""
@Author         : Ailitonia
@Date           : 2022/12/04 16:59
@FileName       : subscription_source.py
@Project        : nonebot2_miya
@Description    : SubscriptionSource DAL
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from datetime import datetime
from typing import Annotated

from pydantic import Field
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.compat import parse_obj_as
from ..model import BaseDataAccessLayer, BaseDataOutModel
from ..schema import SubscriptionSourceOrm


class _SubscribedEntity(BaseDataOutModel):
    """已订阅实体对象数据"""
    id: int
    bot_index_id: int
    entity_type: str
    entity_id: str
    entity_name: str


class SubscriptionSource(BaseDataOutModel):
    """订阅源数据"""
    id: int
    sub_type: str
    sub_id: str
    sub_user_name: str
    sub_info: str | None
    created_at: datetime | None
    updated_at: datetime | None

    # 级联数据
    entities_subscription_source_had: Annotated[list[_SubscribedEntity], Field(default_factory=list)]


class SubscriptionSourceDAL(BaseDataAccessLayer[SubscriptionSourceOrm, SubscriptionSource]):
    """订阅源"""

    async def _count_all(self) -> int:
        """查询全表行数"""
        stmt = select(func.count()).select_from(SubscriptionSourceOrm)
        return (await self.db_session.execute(stmt)).scalar_one()

    async def _clear_all(self) -> None:
        """清空全表, 敏感操作, 方法内不执行 commit, 可由外层事务 rollback"""
        await self.db_session.execute(delete(SubscriptionSourceOrm))
        self.db_session.expunge_all()

    async def _select_unique(
            self,
            sub_type: str,
            sub_id: str,
            *,
            populate_existing: bool = False,
            with_for_update: bool = False,
            nowait_for_update: bool = False,
    ) -> SubscriptionSourceOrm:
        stmt = (select(SubscriptionSourceOrm)
                .options(selectinload(SubscriptionSourceOrm.entities_subscription_source_had))
                .where(SubscriptionSourceOrm.sub_type == sub_type)
                .where(SubscriptionSourceOrm.sub_id == sub_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        if with_for_update:
            stmt = stmt.with_for_update(nowait=nowait_for_update)

        return (await self.db_session.execute(stmt)).scalar_one()

    async def query_unique(
            self,
            sub_type: str,
            sub_id: str,
            *,
            populate_existing: bool = False,
    ) -> SubscriptionSource:
        item = await self._select_unique(
            sub_type,
            sub_id,
            populate_existing=populate_existing,
        )
        return SubscriptionSource.model_validate(item)

    async def query_all(
            self,
            *,
            populate_existing: bool = False,
    ) -> list[SubscriptionSource]:
        stmt = (select(SubscriptionSourceOrm)
                .options(selectinload(SubscriptionSourceOrm.entities_subscription_source_had))
                .order_by(SubscriptionSourceOrm.sub_type, SubscriptionSourceOrm.sub_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[SubscriptionSource], (await self.db_session.execute(stmt)).scalars().all())

    async def query_type_all(
            self,
            sub_type: str,
            *,
            populate_existing: bool = False,
    ) -> list[SubscriptionSource]:
        """查询 sub_type 对应的全部订阅源"""
        stmt = (select(SubscriptionSourceOrm)
                .options(selectinload(SubscriptionSourceOrm.entities_subscription_source_had))
                .where(SubscriptionSourceOrm.sub_type == sub_type)
                .order_by(SubscriptionSourceOrm.sub_type, SubscriptionSourceOrm.sub_id))

        if populate_existing:
            stmt = stmt.execution_options(populate_existing=True)

        return parse_obj_as(list[SubscriptionSource], (await self.db_session.execute(stmt)).scalars().all())

    async def add_update_exist(
            self,
            sub_type: str,
            sub_id: str,
            sub_user_name: str,
            sub_info: str | None = None,
    ) -> SubscriptionSource:
        """向数据库插入新行, 存在则更新

        通过捕获异常实现, 性能较差, 且并发时仍可能出现死锁或需要重试

        Note: SQLite 后端在嵌套事务 (SAVEPOINT) 场景下, 插入分支可能因驱动 legacy 事务控制
        (会话事务不显式发送 BEGIN, SAVEPOINT 直接开启物理事务且 RELEASE 即提交) 而被提前提交,
        外层事务 rollback 无法撤销; MySQL/PostgreSQL 后端不受影响
        """
        new_obj = SubscriptionSourceOrm(
            sub_type=sub_type,
            sub_id=sub_id,
            sub_user_name=sub_user_name,
            sub_info=sub_info,
        )

        try:
            async with self.safe_begin_transaction() as session:
                session.add(new_obj)
                await session.flush()
        except IntegrityError as e:
            # 只有唯一约束冲突才进入"已存在则更新"分支, 其他完整性冲突(外键/非空等)原样抛出
            if not self._is_unique_conflict_error(e):
                raise
            if new_obj in self.db_session:
                self.db_session.expunge(new_obj)
            async with self.safe_begin_transaction() as session:
                exist_obj = await self._select_unique(
                    sub_type,
                    sub_id,
                    populate_existing=True,
                    with_for_update=True,
                )
                exist_obj.sub_user_name = sub_user_name
                exist_obj.sub_info = sub_info
                await session.flush()

        # 重新加载订阅源及其订阅实体, 确保返回数据模型时关系属性已加载
        source_item = await self._select_unique(sub_type, sub_id, populate_existing=True)
        return SubscriptionSource.model_validate(source_item)

    async def delete(self, sub_type: str, sub_id: str) -> None:
        stmt = (delete(SubscriptionSourceOrm)
                .where(SubscriptionSourceOrm.sub_type == sub_type)
                .where(SubscriptionSourceOrm.sub_id == sub_id))
        await self.db_session.execute(stmt)


__all__ = [
    'SubscriptionSource',
    'SubscriptionSourceDAL',
]
