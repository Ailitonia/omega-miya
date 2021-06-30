from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import User, Skill, UserSkill, Vacation
from .skill import DBSkill
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBUser(object):
    def __init__(self, user_id: int):
        self.qq = user_id

    async def id(self) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.id).where(User.qq == self.qq)
                    )
                    user_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=user_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def nickname(self) -> Result.TextResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.nickname).where(User.qq == self.qq)
                    )
                    user_nickname = session_result.scalar_one()
                    result = Result.TextResult(error=False, info='Success', result=user_nickname)
                except NoResultFound:
                    result = Result.TextResult(error=True, info='NoResultFound', result='')
                except MultipleResultsFound:
                    result = Result.TextResult(error=True, info='MultipleResultsFound', result='')
                except Exception as e:
                    result = Result.TextResult(error=True, info=repr(e), result='')
        return result

    async def add(self, nickname: str, aliasname: str = None) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        # 用户已存在则更新成员表昵称
                        session_result = await session.execute(
                            select(User).where(User.qq == self.qq)
                        )
                        exist_user = session_result.scalar_one()
                        if exist_user.nickname == nickname:
                            result = Result.IntResult(error=False, info='Nickname not change', result=0)
                        else:
                            exist_user.nickname = nickname
                            exist_user.aliasname = aliasname
                            exist_user.updated_at = datetime.now()
                            result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在则成员表中添加新成员
                        new_user = User(qq=self.qq, nickname=nickname, aliasname=aliasname, created_at=datetime.now())
                        session.add(new_user)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def delete(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 删除用户表中用户
                    session_result = await session.execute(
                        select(User).where(User.qq == self.qq)
                    )
                    exist_user = session_result.scalar_one()
                    await session.delete(exist_user)
                await session.commit()
                result = Result.IntResult(error=False, info='Success Delete', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_list(self) -> Result.ListResult:
        id_result = await self.id()
        if id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Skill.name, UserSkill.skill_level).
                        join(UserSkill).
                        where(Skill.id == UserSkill.skill_id).
                        where(UserSkill.user_id == id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def skill_add(self, skill: DBSkill, skill_level: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 查询用户已有技能
                    try:
                        # 已有技能, 更新等级
                        session_result = await session.execute(
                            select(UserSkill).
                            where(UserSkill.skill_id == skill_id_result.result).
                            where(UserSkill.user_id == user_id_result.result)
                        )
                        exist_skill = session_result.scalar_one()
                        exist_skill.skill_level = skill_level
                        exist_skill.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_skill = UserSkill(user_id=user_id_result.result, skill_id=skill_id_result.result,
                                              skill_level=skill_level, created_at=datetime.now())
                        session.add(new_skill)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_del(self, skill: DBSkill) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSkill).
                        where(UserSkill.skill_id == skill_id_result.result).
                        where(UserSkill.user_id == user_id_result.result)
                    )
                    exist_skill = session_result.scalar_one()
                    await session.delete(exist_skill)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except NoResultFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def skill_clear(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserSkill).where(UserSkill.user_id == user_id_result.result)
                    )
                    for exist_skill in session_result.scalars().all():
                        await session.delete(exist_skill)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def status(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Vacation.status).where(Vacation.user_id == user_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def vacation_status(self) -> Result.ListResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.ListResult(error=True, info='User not exist', result=[-1, None])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Vacation.status, Vacation.stop_at).
                        where(Vacation.user_id == user_id_result.result)
                    )
                    res = session_result.one()
                    result = Result.ListResult(error=False, info='Success', result=[res[0], res[1]])
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[-1, None])
        return result

    async def status_set(self, status: int) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Vacation).where(Vacation.user_id == user_id_result.result)
                        )
                        exist_status = session_result.scalar_one()
                        exist_status.status = status
                        exist_status.stop_at = None
                        exist_status.reason = None
                        exist_status.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_status = Vacation(user_id=user_id_result.result, status=status, created_at=datetime.now())
                        session.add(new_status)
                        result = Result.IntResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def vacation_set(self, stop_time: datetime, reason: str = None) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Vacation).where(Vacation.user_id == user_id_result.result)
                        )
                        exist_status = session_result.scalar_one()
                        exist_status.status = 1
                        exist_status.stop_at = stop_time
                        exist_status.reason = reason
                        exist_status.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_status = Vacation(user_id=user_id_result.result, status=1,
                                              stop_at=stop_time, reason=reason, created_at=datetime.now())
                        session.add(new_status)
                        result = Result.IntResult(error=False, info='Success set', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def status_del(self) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Vacation).where(Vacation.user_id == user_id_result.result)
                    )
                    exist_status = session_result.scalar_one()
                    await session.delete(exist_status)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
