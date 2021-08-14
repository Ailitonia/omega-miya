from typing import List, Optional
from datetime import date, datetime
from dataclasses import dataclass
from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import User, UserFavorability, UserSignIn, Skill, UserSkill, Vacation
from .skill import DBSkill
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBUser(object):
    def __init__(self, user_id: int):
        self.qq = user_id

    @dataclass
    class DateListResult(Result.AnyResult):
        result: List[date]

        def __repr__(self):
            return f'<DateListResult(error={self.error}, info={self.info}, result={self.result})>'

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
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
        async_session = BaseDB().get_async_session()
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
        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

        async_session = BaseDB().get_async_session()
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

    async def sign_in(self, *, sign_in_info: Optional[str] = 'Normal sign in') -> Result.IntResult:
        """
        签到
        :param sign_in_info: 签到信息
        :return: IntResult
            1: 已签到
            0: 签到成功
            -1: 错误
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        datetime_now = datetime.now()
        date_now = datetime_now.date()

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(UserSignIn).
                            where(UserSignIn.user_id == user_id_result.result).
                            where(UserSignIn.sign_in_date == date_now)
                        )
                        # 已有签到记录
                        exist_sign_in = session_result.scalar_one()
                        exist_sign_in.sign_in_info = 'Duplicate sign in'
                        exist_sign_in.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=1)
                    except NoResultFound:
                        sign_in = UserSignIn(user_id=user_id_result.result, sign_in_date=date_now,
                                             sign_in_info=sign_in_info, created_at=datetime.now())
                        session.add(sign_in)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def sign_in_statistics(self) -> DateListResult:
        """
        查询所有签到记录
        :return: Result: List[sign_in_date]
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return self.DateListResult(error=True, info='User not exist', result=[])

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(UserSignIn.sign_in_date).
                        where(UserSignIn.user_id == user_id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = self.DateListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = self.DateListResult(error=True, info=repr(e), result=[])
        return result

    async def sign_in_continuous_days(self) -> Result.IntResult:
        """
        查询到目前为止最长连续签到日数
        """
        sign_in_statistics_result = await self.sign_in_statistics()
        if sign_in_statistics_result.error:
            return Result.IntResult(error=True, info=sign_in_statistics_result.info, result=-1)

        # 还没有签到过
        if not sign_in_statistics_result.result:
            return Result.IntResult(error=False, info='Success with sign in not found', result=0)

        datetime_now = datetime.now()
        date_now = datetime_now.date()
        date_now_toordinal = date_now.toordinal()

        # 先将签到记录中的日期转化为整数便于比较
        all_sign_in_list = list(set([x.toordinal() for x in sign_in_statistics_result.result]))
        # 去重后由大到小排序
        all_sign_in_list.sort(reverse=True)

        # 如果今日日期不等于已签到日期最大值, 说明今日没有签到, 则连签日数为0
        if date_now_toordinal != all_sign_in_list[0]:
            return Result.IntResult(error=False, info='Success with not sign in today', result=0)

        # 从大到小检查(即日期从后向前检查), 如果当日序号大小大于与今日日期之差, 说明在这里断签了
        for index, value in enumerate(all_sign_in_list):
            if index != date_now_toordinal - value:
                return Result.IntResult(error=False, info='Success with found interrupt', result=index)
        else:
            # 如果全部遍历完了那就说明全部没有断签
            return Result.IntResult(error=False, info='Success with all continuous', result=len(all_sign_in_list))

    async def favorability_status(self) -> Result.TupleResult:
        """
        查询好感度记录
        :return: Result:
        Tuple[status: str, mood: float, favorability: float, energy: float, currency: float, response_threshold: float]
        """
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.TupleResult(error=True, info='User not exist', result=())

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(UserFavorability.status,
                               UserFavorability.mood,
                               UserFavorability.favorability,
                               UserFavorability.energy,
                               UserFavorability.currency,
                               UserFavorability.response_threshold).
                        where(UserFavorability.user_id == user_id_result.result)
                    )
                    res = session_result.one()
                    result = Result.TupleResult(error=False, info='Success', result=res)
                except NoResultFound:
                    result = Result.TupleResult(error=True, info='NoResultFound', result=())
                except MultipleResultsFound:
                    result = Result.TupleResult(error=True, info='MultipleResultsFound', result=())
                except Exception as e:
                    result = Result.TupleResult(error=True, info=repr(e), result=())
        return result

    async def favorability_reset(
            self,
            *,
            status: str = 'normal',
            mood: float = 0,
            favorability: float = 0,
            energy: float = 0,
            currency: float = 0,
            response_threshold: float = 0
    ) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(UserFavorability).
                            where(UserFavorability.user_id == user_id_result.result)
                        )
                        # 已有好感度记录条目
                        exist_favorability = session_result.scalar_one()
                        exist_favorability.status = status
                        exist_favorability.mood = mood
                        exist_favorability.favorability = favorability
                        exist_favorability.energy = energy
                        exist_favorability.currency = currency
                        exist_favorability.response_threshold = response_threshold
                        exist_favorability.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        favorability = UserFavorability(
                            user_id=user_id_result.result, status=status, mood=mood, favorability=favorability,
                            energy=energy, currency=currency, response_threshold=response_threshold,
                            created_at=datetime.now())
                        session.add(favorability)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def favorability_add(
            self,
            *,
            status: Optional[str] = None,
            mood: Optional[float] = None,
            favorability: Optional[float] = None,
            energy: Optional[float] = None,
            currency: Optional[float] = None,
            response_threshold: Optional[float] = None
    ) -> Result.IntResult:
        user_id_result = await self.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserFavorability).
                        where(UserFavorability.user_id == user_id_result.result)
                    )
                    # 已有好感度记录条目
                    exist_favorability = session_result.scalar_one()
                    if status:
                        exist_favorability.status = status
                    if mood:
                        exist_favorability.mood += mood
                    if favorability:
                        exist_favorability.favorability += favorability
                    if energy:
                        exist_favorability.energy += energy
                    if currency:
                        exist_favorability.currency += currency
                    if response_threshold:
                        exist_favorability.response_threshold += response_threshold
                    exist_favorability.updated_at = datetime.now()
                    result = Result.IntResult(error=False, info='Success upgraded', result=0)
                await session.commit()
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
