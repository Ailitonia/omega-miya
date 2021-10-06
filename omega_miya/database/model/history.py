from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import History
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from datetime import datetime


class DBHistory(object):
    def __init__(self, time: int, self_id: int, post_type: str, detail_type: str):
        self.time = time
        self.self_id = self_id
        self.post_type = post_type
        self.detail_type = detail_type

    async def add(self, sub_type: str = 'Undefined', event_id: int = 0, group_id: int = -1, user_id: int = -1,
                  user_name: str = None, raw_data: str = None, msg_data: str = None) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    new_event = History(time=self.time, self_id=self.self_id,
                                        post_type=self.post_type, detail_type=self.detail_type, sub_type=sub_type,
                                        event_id=event_id, group_id=group_id, user_id=user_id, user_name=user_name,
                                        raw_data=raw_data, msg_data=msg_data, created_at=datetime.now())
                    session.add(new_event)
                    result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def search_unique_msg(
            cls,
            self_id: int,
            post_type: str,
            detail_type: str,
            sub_type: str,
            event_id: int,
            group_id: int,
            user_id: int
    ) -> Result.AnyResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(History).
                        where(History.self_id == self_id).
                        where(History.post_type == post_type).
                        where(History.detail_type == detail_type).
                        where(History.sub_type == sub_type).
                        where(History.event_id == event_id).
                        where(History.group_id == group_id).
                        where(History.user_id == user_id)
                    )
                    exist_history = session_result.scalar_one()
                result = Result.AnyResult(error=False, info='Success', result=exist_history)
            except NoResultFound:
                result = Result.AnyResult(error=True, info='NoResultFound', result=None)
            except MultipleResultsFound:
                result = Result.AnyResult(error=True, info='MultipleResultsFound', result=None)
            except Exception as e:
                result = Result.AnyResult(error=True, info=repr(e), result=None)
        return result

    @classmethod
    async def search_msgs(
            cls,
            self_id: int,
            post_type: str,
            detail_type: str,
            sub_type: str = 'Undefined',
            event_id: int = 0,
            group_id: int = -1,
            user_id: int = -1
    ) -> Result.ListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(History).
                        where(History.self_id == self_id).
                        where(History.post_type == post_type).
                        where(History.detail_type == detail_type).
                        where(History.sub_type == sub_type).
                        where(History.event_id == event_id).
                        where(History.group_id == group_id).
                        where(History.user_id == user_id).
                        order_by(History.time.desc())
                    )
                    exist_history = [x for x in session_result.scalars()]
                result = Result.ListResult(error=False, info='Success', result=exist_history)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def search_msgs_data(
            cls,
            self_id: int,
            post_type: str,
            detail_type: str,
            sub_type: str = 'Undefined',
            event_id: int = 0,
            group_id: int = -1,
            user_id: int = -1
    ) -> Result.TextListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(History.msg_data).
                        where(History.self_id == self_id).
                        where(History.post_type == post_type).
                        where(History.detail_type == detail_type).
                        where(History.sub_type == sub_type).
                        where(History.event_id == event_id).
                        where(History.group_id == group_id).
                        where(History.user_id == user_id).
                        order_by(History.time.desc())
                    )
                    exist_history = [x for x in session_result.scalars()]
                result = Result.TextListResult(error=False, info='Success', result=exist_history)
            except NoResultFound:
                result = Result.TextListResult(error=True, info='NoResultFound', result=[])
            except Exception as e:
                result = Result.TextListResult(error=True, info=repr(e), result=[])
        return result
