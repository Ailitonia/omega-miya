"""
@Author         : Ailitonia
@Date           : 2021/06/01 21:02
@FileName       : pixiv_user_artwork.py
@Project        : nonebot2_miya 
@Description    : PixivUserArtwork Model
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import PixivUserArtwork
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBPixivUserArtwork(object):
    def __init__(self, pid: int, uid: int):
        self.pid = pid
        self.uid = uid

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(PixivUserArtwork.id).
                        where(PixivUserArtwork.pid == self.pid).
                        where(PixivUserArtwork.uid == self.uid)
                    )
                    artwork_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=artwork_table_id)
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

    async def add(self, uname: str, title: str) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(PixivUserArtwork).
                            where(PixivUserArtwork.pid == self.pid).
                            where(PixivUserArtwork.uid == self.uid)
                        )
                        exist_artwork = session_result.scalar_one()
                        exist_artwork.uname = uname
                        exist_artwork.title = title
                        exist_artwork.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Exist artwork updated', result=0)
                    except NoResultFound:
                        new_artwork = PixivUserArtwork(pid=self.pid, uid=self.uid,
                                                       title=title, uname=uname, created_at=datetime.now())
                        session.add(new_artwork)
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
    async def list_all_artwork(cls) -> Result.IntListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(PixivUserArtwork.pid).order_by(PixivUserArtwork.pid)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_artwork_by_uid(cls, uid: int) -> Result.IntListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(PixivUserArtwork.pid).
                        where(PixivUserArtwork.uid == uid).
                        order_by(PixivUserArtwork.pid)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result
