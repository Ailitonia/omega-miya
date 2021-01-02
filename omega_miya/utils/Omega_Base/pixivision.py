from .database import NBdb, DBResult
from .tables import Pixivision
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBPixivision(object):
    def __init__(self, aid: int):
        self.aid = aid

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            pixivision_table_id = session.query(Pixivision.id).filter(Pixivision.aid == self.aid).one()[0]
            result = DBResult(error=False, info='Success', result=pixivision_table_id)
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

    def add(self, title: str, description: str, tags: str, illust_id: str, url: str) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_pixivision = session.query(Pixivision).filter(Pixivision.aid == self.aid).one()
            exist_pixivision.title = title
            exist_pixivision.description = description
            exist_pixivision.tags = tags
            exist_pixivision.illust_id = illust_id
            exist_pixivision.url = url
            exist_pixivision.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgrade', result=0)
        except NoResultFound:
            try:
                # 动态表中添加新动态
                new_pixivision = Pixivision(aid=self.aid, title=title, description=description, tags=tags,
                                            illust_id=illust_id, url=url, created_at=datetime.now())
                session.add(new_pixivision)
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
