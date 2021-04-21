from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Subscription, Group, GroupSub
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBSubscription(object):
    def __init__(self, sub_type: int, sub_id: int):
        self.sub_type = sub_type
        self.sub_id = sub_id

    async def id(self) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.id).
                        where(Subscription.sub_type == self.sub_type).
                        where(Subscription.sub_id == self.sub_id)
                    )
                    subscription_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=subscription_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def add(self, up_name: str, live_info: str = None) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Subscription).
                            where(Subscription.sub_type == self.sub_type).
                            where(Subscription.sub_id == self.sub_id)
                        )
                        exist_subscription = session_result.scalar_one()
                        exist_subscription.up_name = up_name
                        exist_subscription.live_info = live_info
                        exist_subscription.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_subscription = Subscription(sub_type=self.sub_type, sub_id=self.sub_id,
                                                        up_name=up_name, live_info=live_info, created_at=datetime.now())
                        session.add(new_subscription)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        # 清空持已订阅这个sub的群组
        await self.sub_group_clear()

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Subscription).
                        where(Subscription.sub_type == self.sub_type).
                        where(Subscription.sub_id == self.sub_id)
                    )
                    exist_subscription = session_result.scalar_one()
                    await session.delete(exist_subscription)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def sub_group_list(self) -> Result.ListResult:
        id_result = await self.id()
        if id_result.error:
            return Result.ListResult(error=True, info='Subscription not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.group_id).join(GroupSub).
                        where(Group.id == GroupSub.group_id).
                        where(GroupSub.sub_id == id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def sub_group_clear(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).where(GroupSub.sub_id == id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
