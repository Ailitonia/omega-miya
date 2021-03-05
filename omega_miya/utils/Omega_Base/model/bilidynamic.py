from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Bilidynamic
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBDynamic(object):
    def __init__(self, uid: int, dynamic_id: int):
        self.uid = uid
        self.dynamic_id = dynamic_id

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            bilidynamic_table_id = session.query(Bilidynamic.id).\
                filter(Bilidynamic.uid == self.uid).\
                filter(Bilidynamic.dynamic_id == self.dynamic_id).one()[0]
            result = DBResult(error=False, info='Success', result=bilidynamic_table_id)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def exist(self) -> bool:
        result = self.id().success()
        return result

    def add(self, dynamic_type: int, content: str) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_dynamic = session.query(Bilidynamic).\
                filter(Bilidynamic.uid == self.uid).\
                filter(Bilidynamic.dynamic_id == self.dynamic_id).one()
            exist_dynamic.content += f'\nupdate: {datetime.now()}\n{content}'
            exist_dynamic.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgrade', result=0)
        except NoResultFound:
            try:
                # 动态表中添加新动态
                new_dynamic = Bilidynamic(uid=self.uid, dynamic_id=self.dynamic_id, dynamic_type=dynamic_type,
                                          content=content, created_at=datetime.now())
                session.add(new_dynamic)
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
