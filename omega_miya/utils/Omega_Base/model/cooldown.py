from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import CoolDownEvent
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBCoolDownEvent(object):

    @classmethod
    def add_global_cool_down_event(cls, stop_at: datetime, description: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_event = session.query(CoolDownEvent).filter(CoolDownEvent.event_type == 'global').one()
            exist_event.stop_at = stop_at
            exist_event.description = description
            exist_event.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            try:
                new_event = CoolDownEvent(
                    event_type='global', stop_at=stop_at, description=description, created_at=datetime.now())
                session.add(new_event)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def check_global_cool_down_event(cls) -> DBResult:
        session = NBdb().get_session()
        try:
            event = session.query(CoolDownEvent).filter(CoolDownEvent.event_type == 'global').one()
            stop_at = event.stop_at
            result = DBResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
        except NoResultFound:
            result = DBResult(error=False, info='NoResultFound', result=0)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def add_plugin_cool_down_event(cls, plugin: str, stop_at: datetime, description: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_event = session.query(CoolDownEvent).\
                filter(CoolDownEvent.event_type == 'plugin').\
                filter(CoolDownEvent.plugin == plugin).one()
            exist_event.stop_at = stop_at
            exist_event.description = description
            exist_event.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            try:
                new_event = CoolDownEvent(
                    event_type='plugin', plugin=plugin, stop_at=stop_at, description=description,
                    created_at=datetime.now())
                session.add(new_event)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def check_plugin_cool_down_event(cls, plugin: str) -> DBResult:
        session = NBdb().get_session()
        try:
            event = session.query(CoolDownEvent).\
                filter(CoolDownEvent.event_type == 'plugin').\
                filter(CoolDownEvent.plugin == plugin).one()
            stop_at = event.stop_at
            result = DBResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
        except NoResultFound:
            result = DBResult(error=False, info='NoResultFound', result=0)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def add_group_cool_down_event(
            cls, plugin: str, group_id: int, stop_at: datetime, description: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_event = session.query(CoolDownEvent).\
                filter(CoolDownEvent.event_type == 'group').\
                filter(CoolDownEvent.plugin == plugin).\
                filter(CoolDownEvent.group_id == group_id).one()
            exist_event.stop_at = stop_at
            exist_event.description = description
            exist_event.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            try:
                new_event = CoolDownEvent(
                    event_type='group', plugin=plugin, group_id=group_id, stop_at=stop_at, description=description,
                    created_at=datetime.now())
                session.add(new_event)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def check_group_cool_down_event(cls, plugin: str, group_id: int) -> DBResult:
        session = NBdb().get_session()
        try:
            event = session.query(CoolDownEvent).\
                filter(CoolDownEvent.plugin == plugin).\
                filter(CoolDownEvent.event_type == 'group').\
                filter(CoolDownEvent.group_id == group_id).one()
            stop_at = event.stop_at
            result = DBResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
        except NoResultFound:
            result = DBResult(error=False, info='NoResultFound', result=0)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def add_user_cool_down_event(
            cls,  plugin: str, user_id: int, stop_at: datetime, description: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_event = session.query(CoolDownEvent). \
                filter(CoolDownEvent.plugin == plugin). \
                filter(CoolDownEvent.event_type == 'user').\
                filter(CoolDownEvent.user_id == user_id).one()
            exist_event.stop_at = stop_at
            exist_event.description = description
            exist_event.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            try:
                new_event = CoolDownEvent(
                    event_type='user', plugin=plugin, user_id=user_id, stop_at=stop_at, description=description,
                    created_at=datetime.now())
                session.add(new_event)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def check_user_cool_down_event(cls, plugin: str, user_id: int) -> DBResult:
        session = NBdb().get_session()
        try:
            event = session.query(CoolDownEvent). \
                filter(CoolDownEvent.plugin == plugin). \
                filter(CoolDownEvent.event_type == 'user').\
                filter(CoolDownEvent.user_id == user_id).one()
            stop_at = event.stop_at
            result = DBResult(error=False, info=f'CoolDown until: {stop_at}', result=1)
        except NoResultFound:
            result = DBResult(error=False, info='NoResultFound', result=0)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    @classmethod
    def clear_time_out_event(cls):
        session = NBdb().get_session()
        events = session.query(CoolDownEvent).order_by(CoolDownEvent.id).all()
        for event in events:
            try:
                if datetime.now() >= event.stop_at:
                    session.delete(event)
                    session.commit()
            except Exception:
                session.rollback()
                continue
