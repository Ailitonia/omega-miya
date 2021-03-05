from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Subscription, Group, GroupSub
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBSubscription(object):
    def __init__(self, sub_type: int, sub_id: int):
        self.sub_type = sub_type
        self.sub_id = sub_id

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            subscription_table_id = session.query(Subscription.id).filter(Subscription.sub_type == self.sub_type).\
                filter(Subscription.sub_id == self.sub_id).one()[0]
            result = DBResult(error=False, info='Success', result=subscription_table_id)
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

    def add(self, up_name: str, live_info: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新描述
            exist_subscription = session.query(Subscription).filter(Subscription.sub_type == self.sub_type).\
                filter(Subscription.sub_id == self.sub_id).one()
            exist_subscription.up_name = up_name
            exist_subscription.live_info = live_info
            exist_subscription.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            # 不存在则添加新订阅信息
            try:
                new_subscription = Subscription(sub_type=self.sub_type, sub_id=self.sub_id,
                                                up_name=up_name, live_info=live_info, created_at=datetime.now())
                session.add(new_subscription)
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

    def delete(self) -> DBResult:
        session = NBdb().get_session()
        try:
            # 清空持已订阅这个sub的群组
            self.sub_group_clear()
            exist_subscription = session.query(Subscription).filter(Subscription.sub_type == self.sub_type).\
                filter(Subscription.sub_id == self.sub_id).one()
            session.delete(exist_subscription)
            session.commit()
            result = DBResult(error=False, info='Success', result=0)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def sub_group_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        if self.exist():
            for item in session.query(Group.group_id).join(GroupSub). \
                    filter(Group.id == GroupSub.group_id). \
                    filter(GroupSub.sub_id == self.id().result).all():
                res.append(item[0])
            result = DBResult(error=False, info='Success', result=res)
        else:
            result = DBResult(error=True, info='Subscription not exist', result=res)
        session.close()
        return result

    def sub_group_clear(self) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            try:
                for exist_group_sub in session.query(GroupSub).filter(GroupSub.sub_id == self.id().result).all():
                    session.delete(exist_group_sub)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
            finally:
                session.close()
        else:
            result = DBResult(error=True, info='Subscription not exist', result=-1)
        return result
