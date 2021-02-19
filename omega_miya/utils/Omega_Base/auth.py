from .database import NBdb, DBResult
from .tables import AuthUser, AuthGroup, User, Group
from .user import DBUser
from .group import DBGroup
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBAuth(object):
    def __init__(self, auth_id: int, auth_type: str, auth_node: str):
        """
        :param auth_id: 请求授权id, 用户qq号或群组群号
        :param auth_type:
            user: 用户授权
            group: 群组授权
        :param auth_node: 授权节点
        """
        self.auth_id = auth_id
        self.auth_type = auth_type
        self.auth_node = auth_node

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            if self.auth_type == 'user':
                auth_table_id = session.query(AuthUser.id).join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == self.auth_id). \
                    filter(AuthUser.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            elif self.auth_type == 'group':
                auth_table_id = session.query(AuthGroup.id).join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == self.auth_id). \
                    filter(AuthGroup.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
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

    def set(self, allow_tag: int, deny_tag: int, auth_info: str = None) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新
            if self.auth_type == 'user':
                auth = session.query(AuthUser).join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == self.auth_id). \
                    filter(AuthUser.auth_node == self.auth_node).one()
                auth.allow_tag = allow_tag
                auth.deny_tag = deny_tag
                auth.auth_info = auth_info
                auth.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            elif self.auth_type == 'group':
                auth = session.query(AuthGroup).join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == self.auth_id). \
                    filter(AuthGroup.auth_node == self.auth_node).one()
                auth.allow_tag = allow_tag
                auth.deny_tag = deny_tag
                auth.auth_info = auth_info
                auth.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
        except NoResultFound:
            try:
                # 不存在则添加信息
                if self.auth_type == 'user':
                    user = DBUser(user_id=self.auth_id)
                    if not user.exist():
                        result = DBResult(error=True, info='User not exist', result=-1)
                    else:
                        auth = AuthUser(user_id=user.id().result, auth_node=self.auth_node, allow_tag=allow_tag,
                                        deny_tag=deny_tag, auth_info=auth_info, created_at=datetime.now())
                        session.add(auth)
                        session.commit()
                        result = DBResult(error=False, info='Success set', result=0)
                elif self.auth_type == 'group':
                    group = DBGroup(group_id=self.auth_id)
                    if not group.exist():
                        result = DBResult(error=True, info='Group not exist', result=-1)
                    else:
                        auth = AuthGroup(group_id=group.id().result, auth_node=self.auth_node, allow_tag=allow_tag,
                                         deny_tag=deny_tag, auth_info=auth_info, created_at=datetime.now())
                        session.add(auth)
                        session.commit()
                        result = DBResult(error=False, info='Success set', result=0)
                else:
                    result = DBResult(error=True, info='Auth type error', result=-1)
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

    def allow_tag(self) -> DBResult:
        session = NBdb().get_session()
        try:
            if self.auth_type == 'user':
                auth_table_id = session.query(AuthUser.allow_tag).join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == self.auth_id). \
                    filter(AuthUser.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            elif self.auth_type == 'group':
                auth_table_id = session.query(AuthGroup.allow_tag).join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == self.auth_id). \
                    filter(AuthGroup.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def deny_tag(self) -> DBResult:
        session = NBdb().get_session()
        try:
            if self.auth_type == 'user':
                auth_table_id = session.query(AuthUser.deny_tag).join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == self.auth_id). \
                    filter(AuthUser.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            elif self.auth_type == 'group':
                auth_table_id = session.query(AuthGroup.deny_tag).join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == self.auth_id). \
                    filter(AuthGroup.auth_node == self.auth_node).one()[0]
                result = DBResult(error=False, info='Success', result=auth_table_id)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def delete(self) -> DBResult:
        session = NBdb().get_session()
        try:
            if self.auth_type == 'user':
                auth = session.query(AuthUser).join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == self.auth_id). \
                    filter(AuthUser.auth_node == self.auth_node).one()
                session.delete(auth)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            elif self.auth_type == 'group':
                auth = session.query(AuthGroup).join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == self.auth_id). \
                    filter(AuthGroup.auth_node == self.auth_node).one()
                session.delete(auth)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
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

    @classmethod
    def list(cls, auth_type: str, auth_id: int) -> DBResult:
        session = NBdb().get_session()
        try:
            if auth_type == 'user':
                auth_node_list = session.query(AuthUser.auth_node, AuthUser.allow_tag, AuthUser.deny_tag). \
                    join(User). \
                    filter(AuthUser.user_id == User.id). \
                    filter(User.qq == auth_id).all()
                result = DBResult(error=False, info='Success', result=auth_node_list)
            elif auth_type == 'group':
                auth_node_list = session.query(AuthGroup.auth_node, AuthGroup.allow_tag, AuthGroup.deny_tag). \
                    join(Group). \
                    filter(AuthGroup.group_id == Group.id). \
                    filter(Group.group_id == auth_id).all()
                result = DBResult(error=False, info='Success', result=auth_node_list)
            else:
                result = DBResult(error=True, info='Auth type error', result=-1)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=-1)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=-1)
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result
