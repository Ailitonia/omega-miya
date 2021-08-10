from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Bilidynamic
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBDynamic(object):
    def __init__(self, uid: int, dynamic_id: int):
        self.uid = uid
        self.dynamic_id = dynamic_id

    async def id(self) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Bilidynamic.id).
                        where(Bilidynamic.uid == self.uid).
                        where(Bilidynamic.dynamic_id == self.dynamic_id)
                    )
                    bilidynamic_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=bilidynamic_table_id)
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

    async def add(self, dynamic_type: int, content: str) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Bilidynamic).
                            where(Bilidynamic.uid == self.uid).
                            where(Bilidynamic.dynamic_id == self.dynamic_id)
                        )
                        exist_dynamic = session_result.scalar_one()
                        exist_dynamic.content += f'\nupdate: {datetime.now()}\n{content}'
                        exist_dynamic.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgrade', result=0)
                    except NoResultFound:
                        # 动态表中添加新动态
                        new_dynamic = Bilidynamic(uid=self.uid, dynamic_id=self.dynamic_id, dynamic_type=dynamic_type,
                                                  content=content, created_at=datetime.now())
                        session.add(new_dynamic)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def list_all_dynamic(cls) -> Result.IntListResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Bilidynamic.dynamic_id).order_by(Bilidynamic.dynamic_id)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_dynamic_by_uid(cls, uid: int) -> Result.IntListResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Bilidynamic.dynamic_id).
                        where(Bilidynamic.uid == uid).
                        order_by(Bilidynamic.dynamic_id)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result
