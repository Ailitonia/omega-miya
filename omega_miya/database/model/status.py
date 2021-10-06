from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import OmegaStatus
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBStatus(object):
    def __init__(self, name: str):
        self.name = name

    async def get_status(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(OmegaStatus.status).where(OmegaStatus.name == self.name)
                    )
                    status = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=status)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def set_status(self, status: int, info: str = None) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
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
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在则添加信息
                        new_status = OmegaStatus(name=self.name, status=status, info=info, created_at=datetime.now())
                        session.add(new_status)
                        result = Result.IntResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
