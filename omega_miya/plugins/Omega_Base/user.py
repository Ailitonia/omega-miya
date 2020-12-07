from .database import NBdb, DBResult
from .tables import User, UserGroup
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBUser(object):
    def __init__(self, user_id: int):
        self.qq = user_id

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            user_table_id = session.query(User.id).filter(User.qq == self.qq).one()[0]
            result = DBResult(error=False, info='Success', result=user_table_id)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def exist(self) -> bool:
        result = self.id().success()
        return result

    def add(self, nickname: str) -> DBResult:
        session = NBdb().get_session()
        try:
            # 用户已存在则更新成员表昵称
            exist_user = session.query(User).filter(User.qq == self.qq).one()
            exist_user.nickname = nickname
            exist_user.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            # 不存在则成员表中添加新成员
            try:
                new_user = User(qq=self.qq, nickname=nickname, created_at=datetime.now())
                session.add(new_user)
                session.commit()
                result = DBResult(error=False, info='Success added', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=str(e), result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def delete(self) -> DBResult:
        session = NBdb().get_session()
        try:
            for exist_user in session.query(UserGroup).filter(UserGroup.user_id == self.id().result).all():
                session.delete(exist_user)
            exist_user = session.query(User).filter(User.qq == self.qq).one()
            session.delete(exist_user)
            session.commit()
            result = DBResult(error=False, info='Success', result=0)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def vocation_reset(self) -> DBResult:
        pass
        # TODO
