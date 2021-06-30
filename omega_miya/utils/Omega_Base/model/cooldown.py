from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import CoolDownEvent
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBCoolDownEvent(object):
    @classmethod
    async def add_global_cool_down_event(cls, stop_at: datetime, description: str = None) -> Result.IntResult:
        """
        :return:
            result = 0: Success
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(CoolDownEvent).
                            where(CoolDownEvent.event_type == 'global')
                        )
                        exist_event = session_result.scalar_one()
                        exist_event.stop_at = stop_at
                        exist_event.description = description
                        exist_event.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_event = CoolDownEvent(
                            event_type='global', stop_at=stop_at, description=description, created_at=datetime.now())
                        session.add(new_event)
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
    async def check_global_cool_down_event(cls) -> Result.IntResult:
        """
        :return:
            result = 2: Success with CoolDown Event expired
            result = 1: Success with CoolDown Event exist
            result = 0: Success with CoolDown Event not found
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(CoolDownEvent).
                        where(CoolDownEvent.event_type == 'global')
                    )
                    event = session_result.scalar_one()
                    stop_at = event.stop_at
                    if datetime.now() > stop_at:
                        result = Result.IntResult(error=False, info='Success, CoolDown expired', result=2)
                    else:
                        result = Result.IntResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
                except NoResultFound:
                    result = Result.IntResult(error=False, info='NoResultFound', result=0)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def add_plugin_cool_down_event(
            cls, plugin: str, stop_at: datetime, description: str = None) -> Result.IntResult:
        """
        :return:
            result = 0: Success
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(CoolDownEvent).
                            where(CoolDownEvent.event_type == 'plugin').
                            where(CoolDownEvent.plugin == plugin)
                        )
                        exist_event = session_result.scalar_one()
                        exist_event.stop_at = stop_at
                        exist_event.description = description
                        exist_event.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_event = CoolDownEvent(
                            event_type='plugin', plugin=plugin, stop_at=stop_at, description=description,
                            created_at=datetime.now())
                        session.add(new_event)
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
    async def check_plugin_cool_down_event(cls, plugin: str) -> Result.IntResult:
        """
        :return:
            result = 2: Success with CoolDown Event expired
            result = 1: Success with CoolDown Event exist
            result = 0: Success with CoolDown Event not found
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(CoolDownEvent).
                        where(CoolDownEvent.event_type == 'plugin').
                        where(CoolDownEvent.plugin == plugin)
                    )
                    event = session_result.scalar_one()
                    stop_at = event.stop_at
                    if datetime.now() > stop_at:
                        result = Result.IntResult(error=False, info='Success, CoolDown expired', result=2)
                    else:
                        result = Result.IntResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
                except NoResultFound:
                    result = Result.IntResult(error=False, info='NoResultFound', result=0)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def add_group_cool_down_event(
            cls, plugin: str, group_id: int, stop_at: datetime, description: str = None) -> Result.IntResult:
        """
        :return:
            result = 0: Success
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(CoolDownEvent).
                            where(CoolDownEvent.event_type == 'group').
                            where(CoolDownEvent.plugin == plugin).
                            where(CoolDownEvent.group_id == group_id)
                        )
                        exist_event = session_result.scalar_one()
                        exist_event.stop_at = stop_at
                        exist_event.description = description
                        exist_event.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_event = CoolDownEvent(
                            event_type='group', plugin=plugin, group_id=group_id, stop_at=stop_at,
                            description=description, created_at=datetime.now())
                        session.add(new_event)
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
    async def check_group_cool_down_event(cls, plugin: str, group_id: int) -> Result.IntResult:
        """
        :return:
            result = 2: Success with CoolDown Event expired
            result = 1: Success with CoolDown Event exist
            result = 0: Success with CoolDown Event not found
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(CoolDownEvent).
                        where(CoolDownEvent.event_type == 'group').
                        where(CoolDownEvent.plugin == plugin).
                        where(CoolDownEvent.group_id == group_id)
                    )
                    event = session_result.scalar_one()
                    stop_at = event.stop_at
                    if datetime.now() > stop_at:
                        result = Result.IntResult(error=False, info='Success, CoolDown expired', result=2)
                    else:
                        result = Result.IntResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
                except NoResultFound:
                    result = Result.IntResult(error=False, info='NoResultFound', result=0)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def add_user_cool_down_event(
            cls,  plugin: str, user_id: int, stop_at: datetime, description: str = None) -> Result.IntResult:
        """
        :return:
            result = 0: Success
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(CoolDownEvent).
                            where(CoolDownEvent.event_type == 'user').
                            where(CoolDownEvent.plugin == plugin).
                            where(CoolDownEvent.user_id == user_id)
                        )
                        exist_event = session_result.scalar_one()
                        exist_event.stop_at = stop_at
                        exist_event.description = description
                        exist_event.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_event = CoolDownEvent(
                            event_type='user', plugin=plugin, user_id=user_id, stop_at=stop_at, description=description,
                            created_at=datetime.now())
                        session.add(new_event)
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
    async def check_user_cool_down_event(cls, plugin: str, user_id: int) -> Result.IntResult:
        """
        :return:
            result = 2: Success with CoolDown Event expired
            result = 1: Success with CoolDown Event exist
            result = 0: Success with CoolDown Event not found
            result = -1: Error
        """
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(CoolDownEvent).
                        where(CoolDownEvent.event_type == 'user').
                        where(CoolDownEvent.plugin == plugin).
                        where(CoolDownEvent.user_id == user_id)
                    )
                    event = session_result.scalar_one()
                    stop_at = event.stop_at
                    if datetime.now() > stop_at:
                        result = Result.IntResult(error=False, info='Success, CoolDown expired', result=2)
                    else:
                        result = Result.IntResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
                except NoResultFound:
                    result = Result.IntResult(error=False, info='NoResultFound', result=0)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def clear_time_out_event(cls):
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                session_result = await session.execute(
                    select(CoolDownEvent).order_by(CoolDownEvent.id)
                )
                events = session_result.scalars().all()
            for event in events:
                try:
                    if datetime.now() >= event.stop_at:
                        await session.delete(event)
                        await session.commit()
                except Exception:
                    await session.rollback()
                    continue
