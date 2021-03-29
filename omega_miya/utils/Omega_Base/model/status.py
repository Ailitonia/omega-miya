from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import OmegaStatus
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBStatus(object):
    def __init__(self, name: str):
        self.name = name

    def get_status(self):
        session = NBdb().get_session()
        try:
            status = session.query(OmegaStatus.status).filter(OmegaStatus.name == self.name).one()[0]
            result = DBResult(error=False, info='Success', result=status)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def set_status(self, status: int, info: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新
            exist_status = session.query(OmegaStatus).filter(OmegaStatus.name == self.name).one()
            exist_status.status = status
            exist_status.info = info
            exist_status.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            try:
                # 不存在则添加信息
                new_status = OmegaStatus(name=self.name, status=status, info=info, created_at=datetime.now())
                session.add(new_status)
                session.commit()
                result = DBResult(error=False, info='Success set', result=0)
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
