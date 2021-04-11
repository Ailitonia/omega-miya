from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Pixivision
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBPixivision(object):
    def __init__(self, aid: int):
        self.aid = aid

    async def id(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Pixivision.id).where(Pixivision.aid == self.aid)
                    )
                    pixivision_table_id = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=pixivision_table_id)
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

    async def add(self, title: str, description: str, tags: str, illust_id: str, url: str) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Pixivision).
                            where(Pixivision.aid == self.aid)
                        )
                        exist_pixivision = session_result.scalar_one()
                        exist_pixivision.title = title
                        exist_pixivision.description = description
                        exist_pixivision.tags = tags
                        exist_pixivision.illust_id = illust_id
                        exist_pixivision.url = url
                        exist_pixivision.updated_at = datetime.now()
                        result = DBResult(error=False, info='Success upgrade', result=0)
                    except NoResultFound:
                        new_pixivision = Pixivision(aid=self.aid, title=title, description=description, tags=tags,
                                                    illust_id=illust_id, url=url, created_at=datetime.now())
                        session.add(new_pixivision)
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result
