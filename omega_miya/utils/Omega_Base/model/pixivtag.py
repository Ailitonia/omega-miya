from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import PixivTag, Pixiv, PixivT2I
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBPixivtag(object):
    def __init__(self, tagname: str):
        self.tagname = tagname

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            pixivtag_table_id = session.query(PixivTag.id).filter(PixivTag.tagname == self.tagname).one()[0]
            result = DBResult(error=False, info='Success', result=pixivtag_table_id)
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

    def add(self) -> DBResult:
        session = NBdb().get_session()
        try:
            exist_pixivtag = session.query(PixivTag).filter(PixivTag.tagname == self.tagname).one()
            result = DBResult(error=False, info='pixivtag exist', result=0)
        except NoResultFound:
            try:
                # 动态表中添加新动态
                new_tag = PixivTag(tagname=self.tagname, created_at=datetime.now())
                session.add(new_tag)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                result = DBResult(error=True, info=repr(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def list_illust(self, nsfw_tag: int) -> DBResult:
        session = NBdb().get_session()
        try:
            pid_list = session.query(Pixiv.pid).join(PixivT2I).join(PixivTag). \
                filter(Pixiv.id == PixivT2I.illust_id). \
                filter(PixivT2I.tag_id == PixivTag.id). \
                filter(Pixiv.nsfw_tag == nsfw_tag). \
                filter(PixivTag.tagname.ilike(f'%{self.tagname}%')).all()
            tag_pid_list = []
            for pid in pid_list:
                tag_pid_list.append(pid[0])
            result = DBResult(error=False, info='Success', result=tag_pid_list)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=[])
        finally:
            session.close()
        return result
