from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import OmegaStatus
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBStatus(object):
    def __init__(self, name: str):
        self.name = name

    async def get_status(self):
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(OmegaStatus.status).where(OmegaStatus.name == self.name)
                    )
                    status = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=status)
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def set_status(self, status: int, info: str = None) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # 已存在则更新
                        session_result = await session.execute(
                            select(OmegaStatus).where(OmegaStatus.name == self.name)
                        )
                        exist_status = session_result.scalar_one()
                        exist_status.status = status
                        exist_status.info = info
                        exist_status.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在则添加信息
                        new_status = OmegaStatus(name=self.name, status=status, info=info, created_at=datetime.now())
                        session.add(new_status)
                        result = DBResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result
