from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Skill, User, UserSkill
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBSkill(object):
    def __init__(self, name: str):
        self.name = name

    def id(self) -> DBResult:
        session = NBdb().get_session()
        try:
            skill_table_id = session.query(Skill.id).filter(Skill.name == self.name).one()[0]
            result = DBResult(error=False, info='Success', result=skill_table_id)
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

    def add(self, description: str) -> DBResult:
        session = NBdb().get_session()
        try:
            # 已存在则更新描述
            exist_skill = session.query(Skill).filter(Skill.name == self.name).one()
            exist_skill.description = description
            exist_skill.updated_at = datetime.now()
            session.commit()
            result = DBResult(error=False, info='Success upgraded', result=0)
        except NoResultFound:
            # 不存在则添加新技能
            try:
                new_skill = Skill(name=self.name, description=description, created_at=datetime.now())
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
        return result

    def delete(self) -> DBResult:
        session = NBdb().get_session()
        try:
            # 清空持有这个技能人的技能
            self.able_member_clear()
            exist_skill = session.query(Skill).filter(Skill.name == self.name).one()
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
        return result

    def able_member_list(self) -> DBResult:
        session = NBdb().get_session()
        res = []
        if self.exist():
            for item in session.query(User.qq).join(UserSkill). \
                    filter(User.id == UserSkill.user_id). \
                    filter(UserSkill.skill_id == self.id().result).all():
                res.append(item[0])
            result = DBResult(error=False, info='Success', result=res)
        else:
            result = DBResult(error=True, info='Skill not exist', result=res)
        session.close()
        return result

    def able_member_clear(self) -> DBResult:
        if self.exist():
            session = NBdb().get_session()
            # 查询成员-技能表中用户-技能关系
            try:
                for exist_user_skill in session.query(UserSkill).filter(UserSkill.skill_id == self.id().result).all():
                    session.delete(exist_user_skill)
                session.commit()
                result = DBResult(error=False, info='Success', result=0)
            except Exception as e:
                session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
            finally:
                session.close()
        else:
            result = DBResult(error=True, info='Skill not exist', result=-1)
        return result
