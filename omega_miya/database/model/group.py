from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import Group
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBGroup(object):
    def __init__(self, group_id: int):
        self.group_id = group_id

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.id).where(Group.group_id == self.group_id)
                    )
                    group_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=group_table_id)
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

    async def name(self) -> Result.TextResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.name).where(Group.group_id == self.group_id)
                    )
                    group_name = session_result.scalar_one()
                    result = Result.TextResult(error=False, info='Success', result=group_name)
                except NoResultFound:
                    result = Result.TextResult(error=True, info='NoResultFound', result='')
                except MultipleResultsFound:
                    result = Result.TextResult(error=True, info='MultipleResultsFound', result='')
                except Exception as e:
                    result = Result.TextResult(error=True, info=repr(e), result='')
        return result

    async def add(self, name: str) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Group).where(Group.group_id == self.group_id)
                        )
                        exist_group = session_result.scalar_one()
                        exist_group.name = name
                        exist_group.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_group = Group(group_id=self.group_id, name=name, created_at=datetime.now())
                        session.add(new_group)
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
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 删除群组表中该群组
                    session_result = await session.execute(
                        select(Group).where(Group.group_id == self.group_id)
                    )
                    exist_group = session_result.scalar_one()
                    await session.delete(exist_group)
                await session.commit()
                result = Result.IntResult(error=False, info='Success Delete', result=0)
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

    @classmethod
    async def list_all_group(cls) -> Result.IntListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Group.group_id).order_by(Group.group_id)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result
