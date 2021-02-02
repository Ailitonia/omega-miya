from typing import List
from .database import NBdb, DBResult
from .tables import Pixiv, PixivTag, PixivT2I
from .pixivtag import DBPixivtag
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import func
from sqlalchemy import or_


class DBPixivillust(object):
    def __init__(self, pid: int):
        self.pid = pid

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            pixiv_table_id = session.query(Pixiv.id).filter(Pixiv.pid == self.pid).one()[0]
            result = DBResult(error=False, info='Success', result=pixiv_table_id)
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

    def add(self, uid: int, title: str, uname: str, nsfw_tag: int, tags: List[str], url: str) -> DBResult:
        session = NBdb().get_session()

        # 将tag写入pixiv_tag表
        for tag in tags:
            _tag = DBPixivtag(tagname=tag)
            _tag.add()

        # 将作品信息写入pixiv_illust表
        try:
            exist_illust = session.query(Pixiv).filter(Pixiv.pid == self.pid).one()
            exist_illust.title = title
            exist_illust.uname = uname
            if nsfw_tag > exist_illust.nsfw_tag:
                exist_illust.nsfw_tag = nsfw_tag
            exist_illust.tags = repr(tags)
            exist_illust.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Exist illust updated', result=0)
        except NoResultFound:
            try:
                new_illust = Pixiv(pid=self.pid, uid=uid, title=title, uname=uname, url=url, nsfw_tag=nsfw_tag,
                                   tags=repr(tags), created_at=datetime.now())
                session.add(new_illust)
                session.commit()

                # 写入tag_pixiv关联表
                # 获取本作品在illust表中的id
                _illust_id_res = self.id()
                if not _illust_id_res.success():
                    raise Exception('illust not find or add failed')
                _illust_id = _illust_id_res.result
                # 根据作品tag依次写入tag_illust表
                for tag in tags:
                    _tag = DBPixivtag(tagname=tag)
                    _tag_id_res = _tag.id()
                    if not _tag_id_res.success():
                        continue
                    _tag_id = _tag_id_res.result
                    try:
                        new_tag_illust = PixivT2I(illust_id=_illust_id, tag_id=_tag_id, created_at=datetime.now())
                        session.add(new_tag_illust)
                        session.commit()
                    except Exception as e:
                        session.rollback()
                        try:
                            # 避免以后查询不到，写入失败就将illust信息一并删除
                            _exist_illust = session.query(Pixiv).filter(Pixiv.pid == self.pid).one()
                            session.delete(_exist_illust)
                            session.commit()
                            raise e
                        except Exception as e:
                            # 这里还出错就没救了x
                            session.rollback()
                            raise e
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
    def rand_illust(cls, num: int, nsfw_tag: int):
        session = NBdb().get_session()
        _res = session.query(Pixiv.pid).filter(Pixiv.nsfw_tag == nsfw_tag).order_by(func.random()).limit(num).all()
        pid_list = []
        for pid in _res:
            pid_list.append(pid[0])
        return pid_list

    @classmethod
    def status(cls):
        session = NBdb().get_session()
        all_count = session.query(func.count(Pixiv.id)).scalar()
        moe_count = session.query(func.count(Pixiv.id)).filter(Pixiv.nsfw_tag == 0).scalar()
        setu_count = session.query(func.count(Pixiv.id)).filter(Pixiv.nsfw_tag == 1).scalar()
        r18_count = session.query(func.count(Pixiv.id)).filter(Pixiv.nsfw_tag == 2).scalar()
        result = {'total': int(all_count), 'moe': int(moe_count), 'setu': int(setu_count), 'r18': int(r18_count)}
        return result

    @classmethod
    def list_illust(cls, nsfw_tag: int, keyword: str) -> DBResult:
        session = NBdb().get_session()
        try:
            pid_list = session.query(Pixiv.pid).join(PixivT2I).join(PixivTag). \
                filter(Pixiv.id == PixivT2I.illust_id). \
                filter(PixivT2I.tag_id == PixivTag.id). \
                filter(Pixiv.nsfw_tag == nsfw_tag). \
                filter(or_(PixivTag.tagname.ilike(f'%{keyword}%'), Pixiv.uname.ilike(f'%{keyword}%'))).all()
            tag_pid_list = []
            for pid in pid_list:
                tag_pid_list.append(pid[0])
            result = DBResult(error=False, info='Success', result=tag_pid_list)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=[])
        finally:
            session.close()
        return result
