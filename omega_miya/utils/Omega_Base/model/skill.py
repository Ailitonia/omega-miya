from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import Skill, User, UserSkill
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBSkill(object):
    def __init__(self, name: str):
        self.name = name

    async def id(self) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Skill.id).where(Skill.name == self.name)
                    )
                    skill_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=skill_table_id)
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

    async def add(self, description: str) -> Result.IntResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Skill).where(Skill.name == self.name)
                        )
                        exist_skill = session_result.scalar_one()
                        exist_skill.description = description
                        exist_skill.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_skill = Skill(name=self.name, description=description, created_at=datetime.now())
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

    async def delete(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        # 清空持有这个技能人的技能
        await self.able_member_clear()

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Skill).where(Skill.name == self.name)
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

    async def able_member_list(self) -> Result.ListResult:
        id_result = await self.id()
        if id_result.error:
            return Result.ListResult(error=True, info='Skill not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.qq).join(UserSkill).
                        where(User.id == UserSkill.user_id).
                        where(UserSkill.skill_id == id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def able_member_clear(self) -> Result.IntResult:
        id_result = await self.id()
        if id_result.error:
            return Result.IntResult(error=True, info='Skill not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 查询成员-技能表中用户-技能关系
                    session_result = await session.execute(
                        select(UserSkill).where(UserSkill.skill_id == id_result.result)
                    )
                    for exist_user_skill in session_result.scalars().all():
                        await session.delete(exist_user_skill)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def list_available_skill(cls) -> Result.TextListResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Skill.name).order_by(Skill.name)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.TextListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.TextListResult(error=True, info=repr(e), result=[])
        return result
