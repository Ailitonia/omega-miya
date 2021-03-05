from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import User, UserGroup, Skill, UserSkill, Vocation
from .skill import DBSkill
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
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def exist(self) -> bool:
        result = self.id().success()
        return result

    def nickname(self) -> DBResult:
        session = NBdb().get_session()
        try:
            user_nickname = session.query(User.nickname).filter(User.qq == self.qq).one()[0]
            result = DBResult(error=False, info='Success', result=user_nickname)
        except NoResultFound:
            result = DBResult(error=True, info='NoResultFound', result='')
        except MultipleResultsFound:
            result = DBResult(error=True, info='MultipleResultsFound', result='')
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result='')
        finally:
            session.close()
        return result

    def add(self, nickname: str) -> DBResult:
        session = NBdb().get_session()
        try:
            # 用户已存在则更新成员表昵称
            exist_user = session.query(User).filter(User.qq == self.qq).one()
            if exist_user.nickname == nickname:
                result = DBResult(error=False, info='Success upgraded', result=0)
            else:
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
            # 清空群成员表中该用户
            for exist_user in session.query(UserGroup).filter(UserGroup.user_id == self.id().result).all():
                session.delete(exist_user)
            # 删除技能
            self.skill_clear()
            # 删除状态和假期
            self.status_del()
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
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def skill_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        if self.exist():
            for item in session.query(Skill.name, UserSkill.skill_level).join(UserSkill). \
                    filter(Skill.id == UserSkill.skill_id). \
                    filter(UserSkill.user_id == self.id().result).all():
                res.append(item)
            result = DBResult(error=False, info='Success', result=res)
        else:
            result = DBResult(error=True, info='User not exist', result=res)
        session.close()
        return result

    def skill_add(self, skill: DBSkill, skill_level: int) -> DBResult:
        if self.exist() and skill.exist():
            session = NBdb().get_session()
            # 查询用户已有技能
            try:
                # 已有技能, 更新等级
                exist_skill = session.query(UserSkill). \
                    filter(UserSkill.skill_id == skill.id().result). \
                    filter(UserSkill.user_id == self.id().result).one()
                exist_skill.skill_level = skill_level
                exist_skill.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            except NoResultFound:
                # 不存在则添加新技能
                try:
                    new_skill = UserSkill(user_id=self.id().result, skill_id=skill.id().result,
                                          skill_level=skill_level, created_at=datetime.now())
                    session.add(new_skill)
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
        else:
            result = DBResult(error=True, info='Skill or user not exist', result=-1)
        return result

    def skill_del(self, skill: DBSkill) -> DBResult:
        if self.exist() and skill.exist():
            session = NBdb().get_session()
            # 查询用户已有技能
            try:
                # 已有技能, 删除
                exist_skill = session.query(UserSkill). \
                    filter(UserSkill.skill_id == skill.id().result). \
                    filter(UserSkill.user_id == self.id().result).one()
                session.delete(exist_skill)
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
        else:
            result = DBResult(error=True, info='Skill or user not exist', result=-1)
        return result

    def skill_clear(self) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            # 查询用户已有技能
            try:
                for exist_skill in session.query(UserSkill).filter(UserSkill.user_id == self.id().result).all():
                    session.delete(exist_skill)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
            finally:
                session.close()
        else:
            result = DBResult(error=True, info='Skill or user not exist', result=-1)
        return result

    def status(self) -> DBResult:
        session = NBdb().get_session()
        try:
            res = session.query(Vocation.status).filter(Vocation.user_id == self.id().result).one()
            result = DBResult(error=False, info='Success', result=res[0])
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=-1)
        finally:
            session.close()
        return result

    def vocation_status(self) -> DBResult:
        session = NBdb().get_session()
        try:
            status, stop_time = session.query(Vocation.status, Vocation.stop_at). \
                filter(Vocation.user_id == self.id().result).one()
            result = DBResult(error=False, info='Success', result=[status, stop_time])
        except Exception as e:
            result = DBResult(error=True, info=repr(e), result=[-1, None])
        finally:
            session.close()
        return result

    def status_set(self, status: int) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            # 检查用户在假期表中是否存在
            try:
                # 存在则设置假期状态信息
                exist_status = session.query(Vocation).filter(Vocation.user_id == self.id().result).one()
                exist_status.status = status
                exist_status.stop_at = None
                exist_status.reason = None
                exist_status.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            except NoResultFound:
                # 不存在则假期表中添加信息
                try:
                    new_status = Vocation(user_id=self.id().result, status=status, created_at=datetime.now())
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
        else:
            result = DBResult(error=True, info='User not exist', result=-1)
        return result

    def vocation_set(self, stop_time: datetime, reason: str = None) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            # 检查用户在假期表中是否存在
            try:
                # 存在则设置假期状态信息
                exist_status = session.query(Vocation).filter(Vocation.user_id == self.id().result).one()
                exist_status.status = 1
                exist_status.stop_at = stop_time
                exist_status.reason = reason
                exist_status.updated_at = datetime.now()
                session.commit()
                result = DBResult(error=False, info='Success upgraded', result=0)
            except NoResultFound:
                # 不存在则假期表中添加信息
                try:
                    new_status = Vocation(user_id=self.id().result, status=1,
                                          stop_at=stop_time, reason=reason, created_at=datetime.now())
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
        else:
            result = DBResult(error=True, info='User not exist', result=-1)
        return result

    def status_del(self) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            try:
                exist_status = session.query(Vocation).filter(Vocation.user_id == self.id().result).one()
                session.delete(exist_status)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
            finally:
                session.close()
        else:
            result = DBResult(error=True, info='Status or user not exist', result=-1)
        return result
