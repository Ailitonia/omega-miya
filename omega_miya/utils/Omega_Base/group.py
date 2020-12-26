from .database import NBdb, DBResult
from .tables import User, Group, UserGroup, Vocation, Skill, UserSkill
from .user import DBUser, DBSkill
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBGroup(object):
    def __init__(self, group_id: int):
        self.group_id = group_id

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            group_table_id = session.query(Group.id).filter(Group.group_id == self.group_id).one()[0]
            result = DBResult(error=False, info='Success', result=group_table_id)
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

    def add(self, name: str) -> DBResult:
        session = NBdb().get_session()
        try:
            # qq群已存在则更新群名称
            exist_group = session.query(Group).filter(Group.group_id == self.group_id).one()
            exist_group.name = name
            exist_group.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            # 不存在则添加新群组
            try:
                new_group = Group(group_id=self.group_id, name=name, notice_permissions=0,
                                  command_permissions=0, permission_level=0, created_at=datetime.now())
                session.add(new_group)
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
            # 清空群成员列表
            self.member_clear()
            # 清空订阅
            # TODO
            exist_group = session.query(Group).filter(Group.group_id == self.group_id).one()
            session.delete(exist_group)
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

    def member_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        if self.exist():
            for item in session.query(User.qq, UserGroup.user_group_nickname).join(UserGroup). \
                    filter(User.id == UserGroup.user_id). \
                    filter(UserGroup.group_id == self.id().result).all():
                res.append(item)
            result = DBResult(error=False, info='Success', result=res)
        else:
            result = DBResult(error=True, info='Group not exist', result=res)
        session.close()
        return result

    def member_add(self, user: DBUser, user_group_nickname: str) -> DBResult:
        if self.exist() and user.exist():
            session = NBdb().get_session()
            # 查询成员-群组表中用户-群关系
            try:
                # 用户-群关系已存在, 更新用户群昵称
                exist_user = session.query(UserGroup). \
                    filter(UserGroup.user_id == user.id().result). \
                    filter(UserGroup.group_id == self.id().result).one()
                exist_user.user_group_nickname = user_group_nickname
                exist_user.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            except NoResultFound:
                # 不存在关系则添加新成员
                try:
                    new_user = UserGroup(user_id=user.id().result, group_id=self.id().result,
                                         user_group_nickname=user_group_nickname, created_at=datetime.now())
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
        else:
            result = DBResult(error=True, info='Group or user not exist', result=-1)
        return result

    def member_del(self, user: DBUser) -> DBResult:
        if self.exist() and user.exist():
            session = NBdb().get_session()
            # 查询成员-群组表中用户-群关系
            try:
                # 用户-群关系已存在, 删除
                exist_user = session.query(UserGroup). \
                    filter(UserGroup.user_id == user.id().result). \
                    filter(UserGroup.group_id == self.id().result).one()
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
        else:
            result = DBResult(error=True, info='Group or user not exist', result=-1)
        return result

    def member_clear(self) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            # 查询成员-群组表中用户-群关系
            try:
                for exist_user in session.query(UserGroup).filter(UserGroup.group_id == self.id().result).all():
                    session.delete(exist_user)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=str(e), result=-1)
            finally:
                session.close()
        else:
            result = DBResult(error=True, info='Group or user not exist', result=-1)
        return result

    def permission_reset(self) -> DBResult:
        session = NBdb().get_session()
        # 检查群组是否在表中, 存在则直接更新状态
        try:
            exist_group = session.query(Group).filter(Group.group_id == self.group_id).one()
            exist_group.notice_permissions = 0
            exist_group.command_permissions = 0
            exist_group.permission_level = 0
            exist_group.updated_at = datetime.now()
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

    def permission_set(self, notice: int = 0, command: int = 0, level: int = 0) -> DBResult:
        session = NBdb().get_session()
        # 检查群组是否在表中, 存在则直接更新状态
        try:
            exist_group = session.query(Group).filter(Group.group_id == self.group_id).one()
            exist_group.notice_permissions = notice
            exist_group.command_permissions = command
            exist_group.permission_level = level
            exist_group.updated_at = datetime.now()
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

    def permission_info(self) -> DBResult:
        session = NBdb().get_session()
        res = {}
        # 检查群组是否在表中, 存在则直接更新状态
        try:
            notice, command, level = session.query(Group.notice_permissions,
                                                   Group.command_permissions,
                                                   Group.permission_level).\
                filter(Group.group_id == self.group_id).one()
            res['notice'] = notice
            res['command'] = command
            res['level'] = level
            result = DBResult(error=False, info='Success', result=res)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result=res)
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result=res)
        except Exception as e:
            session.rollback()
            result = DBResult(error=True, info=str(e), result=res)
        finally:
            session.close()
        return result

    def permission_notice(self) -> DBResult:
        session = NBdb().get_session()
        try:
            res = session.query(Group.notice_permissions).filter(Group.group_id == self.group_id).one()
            if res and res[0] == 1:
                result = DBResult(error=False, info='Success', result=1)
            else:
                result = DBResult(error=False, info='Success', result=0)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def permission_command(self) -> DBResult:
        session = NBdb().get_session()
        try:
            res = session.query(Group.command_permissions).filter(Group.group_id == self.group_id).one()
            if res and res[0] == 1:
                result = DBResult(error=False, info='Success', result=1)
            else:
                result = DBResult(error=False, info='Success', result=0)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def permission_level(self) -> DBResult:
        session = NBdb().get_session()
        try:
            res = session.query(Group.permission_level).filter(Group.group_id == self.group_id).one()
            result = DBResult(error=False, info='Success', result=res[0])
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=-1)
        finally:
            session.close()
        return result

    def idle_member_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        # 查询该群组中所有没有假的人
        try:
            for user_id, nickname in session.query(User.id, UserGroup.user_group_nickname). \
                    join(Vocation).join(UserGroup).join(Group). \
                    filter(User.id == Vocation.user_id). \
                    filter(User.id == UserGroup.user_id). \
                    filter(UserGroup.group_id == Group.id). \
                    filter(Vocation.status == 0). \
                    filter(Group.group_id == self.group_id). \
                    all():
                res_skills = session.query(Skill.name). \
                    join(UserSkill).join(User). \
                    filter(Skill.id == UserSkill.skill_id). \
                    filter(UserSkill.user_id == User.id). \
                    filter(User.id == user_id). \
                    all()
                user_skill = ''
                if res_skills:
                    for skill in res_skills:
                        user_skill += f'/{skill[0]}'
                else:
                    user_skill = '/暂无技能'
                res.append([nickname, user_skill])
            result = DBResult(error=False, info='Success', result=res)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=res)
        finally:
            session.close()
        return result

    def idle_skill_list(self, skill: DBSkill) -> DBResult:
        session = NBdb().get_session()
        res = []
        # 查询这这个技能有那些人会
        try:
            for user_id, nickname in session.query(User.id, UserGroup.user_group_nickname). \
                    join(UserSkill).join(Skill).join(UserGroup).join(Group). \
                    filter(User.id == UserSkill.user_id). \
                    filter(UserSkill.skill_id == Skill.id). \
                    filter(User.id == UserGroup.user_id). \
                    filter(UserGroup.group_id == Group.id). \
                    filter(Skill.name == skill.name). \
                    filter(Group.group_id == self.group_id). \
                    all():
                # 查这个人是不是空闲
                user_status = session.query(Vocation.status).filter(Vocation.user_id == user_id).one()[0]
                # 如果空闲则把这个人昵称放进结果列表里面
                if user_status == 0:
                    res.append(nickname)
            result = DBResult(error=False, info='Success', result=res)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=res)
        finally:
            session.close()
        return result

    def vocation_member_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        # 查询所有没有假的人
        try:
            for nickname, stop_at in session.query(UserGroup.user_group_nickname, Vocation.stop_at).\
                    select_from(UserGroup).join(User).join(Group). \
                    filter(UserGroup.user_id == User.id). \
                    filter(User.id == Vocation.user_id). \
                    filter(UserGroup.group_id == Group.id). \
                    filter(Vocation.status == 1). \
                    filter(Group.group_id == self.group_id). \
                    all():
                res.append([nickname, stop_at])
            result = DBResult(error=False, info='Success', result=res)
        except Exception as e:
            result = DBResult(error=True, info=str(e), result=res)
        finally:
            session.close()
        return result

    def init_member_status(self) -> DBResult:
        memberlist = self.member_list().result
        for user_qq, nickname in memberlist:
            user = DBUser(user_id=user_qq)
            if user.status().error:
                user.status_set(status=0)
        return DBResult(error=False, info='ignore', result=0)
