from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Bilidynamic
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBDynamic(object):
    def __init__(self, uid: int, dynamic_id: int):
        self.uid = uid
        self.dynamic_id = dynamic_id

    async def id(self) -> DBResult:
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
                    result = DBResult(error=False, info='Success', result=bilidynamic_table_id)
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def add(self, dynamic_type: int, content: str) -> DBResult:
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
                        result = DBResult(error=False, info='Success upgrade', result=0)
                    except NoResultFound:
                        # 动态表中添加新动态
                        new_dynamic = Bilidynamic(uid=self.uid, dynamic_id=self.dynamic_id, dynamic_type=dynamic_type,
                                                  content=content, created_at=datetime.now())
                        session.add(new_dynamic)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result
