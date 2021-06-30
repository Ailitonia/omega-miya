from omega_miya.utils.Omega_Base.database import NBdb
from omega_miya.utils.Omega_Base.class_result import Result
from omega_miya.utils.Omega_Base.tables import \
    User, Group, BotGroup, UserGroup, Vacation, Skill, UserSkill, \
    Subscription, GroupSub, GroupSetting, EmailBox, GroupEmailBox
from .user import DBUser
from .skill import DBSkill
from .group import DBGroup
from .bot_self import DBBot
from .subscription import DBSubscription
from .mail import DBEmailBox
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound


class DBBotGroup(DBGroup):
    def __init__(self, group_id: int, self_bot: DBBot):
        super().__init__(group_id)
        self.self_bot = self_bot

    @classmethod
    async def list_exist_bot_groups(cls, self_bot: DBBot) -> Result.ListResult:
        self_bot_id_result = await self_bot.id()
        if self_bot_id_result.error:
            return Result.ListResult(error=True, info='Bot not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group.group_id).
                        join(BotGroup).
                        where(Group.id == BotGroup.group_id).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    exist_groupss = [x for x in session_result.scalars().all()]
                result = Result.ListResult(error=False, info='Success', result=exist_groupss)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_exist_bot_groups_by_notice_permissions(
            cls, notice_permissions: int, self_bot: DBBot) -> Result.ListResult:
        self_bot_id_result = await self_bot.id()
        if self_bot_id_result.error:
            return Result.ListResult(error=True, info='Bot not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group.group_id).
                        join(BotGroup).
                        where(Group.id == BotGroup.group_id).
                        where(BotGroup.bot_self_id == self_bot_id_result.result).
                        where(BotGroup.notice_permissions == notice_permissions)
                    )
                    exist_friends = [x for x in session_result.scalars().all()]
                result = Result.ListResult(error=False, info='Success', result=exist_friends)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_exist_bot_groups_by_command_permissions(
            cls, command_permissions: int, self_bot: DBBot) -> Result.ListResult:
        self_bot_id_result = await self_bot.id()
        if self_bot_id_result.error:
            return Result.ListResult(error=True, info='Bot not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group.group_id).
                        join(BotGroup).
                        where(Group.id == BotGroup.group_id).
                        where(BotGroup.bot_self_id == self_bot_id_result.result).
                        where(BotGroup.command_permissions == command_permissions)
                    )
                    exist_friends = [x for x in session_result.scalars().all()]
                result = Result.ListResult(error=False, info='Success', result=exist_friends)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_exist_bot_groups_by_permission_level(
            cls, permission_level: int, self_bot: DBBot) -> Result.ListResult:
        self_bot_id_result = await self_bot.id()
        if self_bot_id_result.error:
            return Result.ListResult(error=True, info='Bot not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(Group.group_id).
                        join(BotGroup).
                        where(Group.id == BotGroup.group_id).
                        where(BotGroup.bot_self_id == self_bot_id_result.result).
                        where(BotGroup.permission_level >= permission_level)
                    )
                    exist_friends = [x for x in session_result.scalars().all()]
                result = Result.ListResult(error=False, info='Success', result=exist_friends)
            except NoResultFound:
                result = Result.ListResult(error=True, info='NoResultFound', result=[])
            except MultipleResultsFound:
                result = Result.ListResult(error=True, info='MultipleResultsFound', result=[])
            except Exception as e:
                result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def bot_group_id(self) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(BotGroup.id).
                        where(BotGroup.bot_self_id == self_bot_id_result.result).
                        where(BotGroup.group_id == group_id_result.result)
                    )
                    bot_group_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=bot_group_table_id)
            except NoResultFound:
                result = Result.IntResult(error=True, info='NoResultFound', result=-1)
            except MultipleResultsFound:
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.bot_group_id()
        return result.success()

    async def memo(self) -> Result.TextResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.TextResult(error=True, info='Group not exist', result='')

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.TextResult(error=True, info='Bot not exist', result='')

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotGroup.group_memo).
                        where(BotGroup.bot_self_id == self_bot_id_result.result).
                        where(BotGroup.group_id == group_id_result.result)
                    )
                    group_memo = session_result.scalar_one()
                    result = Result.TextResult(error=False, info='Success', result=group_memo)
                except NoResultFound:
                    result = Result.TextResult(error=True, info='NoResultFound', result='')
                except MultipleResultsFound:
                    result = Result.TextResult(error=True, info='MultipleResultsFound', result='')
                except Exception as e:
                    result = Result.TextResult(error=True, info=repr(e), result='')
        return result

    async def set_bot_group(self, group_memo: str = None) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        # 处理群备注过长
        if not group_memo:
            pass
        elif len(group_memo) > 64:
            group_memo = group_memo[:63]

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(BotGroup).
                            where(BotGroup.group_id == group_id_result.result).
                            where(BotGroup.bot_self_id == self_bot_id_result.result)
                        )
                        exist_group = session_result.scalar_one()
                        if group_memo:
                            exist_group.group_memo = group_memo
                        exist_group.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_group = BotGroup(group_id=group_id_result.result, bot_self_id=self_bot_id_result.result,
                                             notice_permissions=0, command_permissions=0, permission_level=0,
                                             group_memo=group_memo, created_at=datetime.now())
                        session.add(new_group)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def del_bot_group(self) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 删除群组表中该群组
                    session_result = await session.execute(
                        select(BotGroup).
                        where(BotGroup.id == bot_group_id_result.result)
                    )
                    exist_group = session_result.scalar_one()
                    await session.delete(exist_group)
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

    async def member_list(self) -> Result.ListResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(User.qq, UserGroup.user_group_nickname).
                        join(UserGroup).
                        where(User.id == UserGroup.user_id).
                        where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def member_add(self, user: DBUser, user_group_nickname: str) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        user_id_result = await user.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    # 查询成员-群组表中用户-群关系
                    try:
                        # 用户-群关系已存在, 更新用户群昵称
                        session_result = await session.execute(
                            select(UserGroup).
                            where(UserGroup.user_id == user_id_result.result).
                            where(UserGroup.group_id == bot_group_id_result.result)
                        )
                        exist_user = session_result.scalar_one()
                        exist_user.user_group_nickname = user_group_nickname
                        exist_user.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        # 不存在关系则添加新成员
                        new_user = UserGroup(user_id=user_id_result.result, group_id=bot_group_id_result.result,
                                             user_group_nickname=user_group_nickname, created_at=datetime.now())
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

    async def member_del(self, user: DBUser) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        user_id_result = await user.id()
        if user_id_result.error:
            return Result.IntResult(error=True, info='User not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserGroup).
                        where(UserGroup.user_id == user_id_result.result).
                        where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    exist_user = session_result.scalar_one()
                    await session.delete(exist_user)
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

    async def member_clear(self) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(UserGroup).where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    for exist_user in session_result.scalars().all():
                        await session.delete(exist_user)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_reset(self) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(BotGroup).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    exist_group = session_result.scalar_one()
                    exist_group.notice_permissions = 0
                    exist_group.command_permissions = 0
                    exist_group.permission_level = 0
                    exist_group.updated_at = datetime.now()
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

    async def permission_set(self, notice: int = 0, command: int = 0, level: int = 0) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(BotGroup).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    exist_group = session_result.scalar_one()
                    exist_group.notice_permissions = notice
                    exist_group.command_permissions = command
                    exist_group.permission_level = level
                    exist_group.updated_at = datetime.now()
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

    async def permission_info(self) -> Result.IntTupleResult:
        """
        :return: Result: Tuple[Notice_permission, Command_permission, Permission_level]
        """
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntTupleResult(error=True, info='Group not exist', result=(-1, -1, -1))

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntTupleResult(error=True, info='Bot not exist', result=(-1, -1, -1))

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotGroup.notice_permissions, BotGroup.command_permissions, BotGroup.permission_level).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    notice, command, level = session_result.one()
                    result = Result.IntTupleResult(error=False, info='Success', result=(notice, command, level))
                except NoResultFound:
                    result = Result.IntTupleResult(error=True, info='NoResultFound', result=(-1, -1, -1))
                except MultipleResultsFound:
                    result = Result.IntTupleResult(error=True, info='MultipleResultsFound', result=(-1, -1, -1))
                except Exception as e:
                    result = Result.IntTupleResult(error=True, info=repr(e), result=(-1, -1, -1))
        return result

    async def permission_notice(self) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotGroup.notice_permissions).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_command(self) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotGroup.command_permissions).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def permission_level(self) -> Result.IntResult:
        group_id_result = await self.id()
        if group_id_result.error:
            return Result.IntResult(error=True, info='Group not exist', result=-1)

        self_bot_id_result = await self.self_bot.id()
        if self_bot_id_result.error:
            return Result.IntResult(error=True, info='Bot not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(BotGroup.permission_level).
                        where(BotGroup.group_id == group_id_result.result).
                        where(BotGroup.bot_self_id == self_bot_id_result.result)
                    )
                    res = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def idle_member_list(self) -> Result.ListResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        res = []
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询该群组中所有没有假的人
                    session_result = await session.execute(
                        select(User.id, UserGroup.user_group_nickname).
                        join(Vacation).join(UserGroup).
                        where(User.id == Vacation.user_id).
                        where(User.id == UserGroup.user_id).
                        where(Vacation.status == 0).
                        where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    user_res = [(x[0], x[1]) for x in session_result.all()]
                    # 查对应每个人的技能
                    for user_id, nickname in user_res:
                        session_result = await session.execute(
                            select(Skill.name).join(UserSkill).join(User).
                            where(Skill.id == UserSkill.skill_id).
                            where(UserSkill.user_id == User.id).
                            where(User.id == user_id)
                        )
                        user_skill_res = [x for x in session_result.scalars().all()]
                        if user_skill_res:
                            user_skill_text = '/'.join(user_skill_res)
                        else:
                            user_skill_text = '暂无技能'
                        res.append((nickname, user_skill_text))
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def idle_skill_list(self, skill: DBSkill) -> Result.ListResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        skill_id_result = await skill.id()
        if skill_id_result.error:
            return Result.ListResult(error=True, info='Skill not exist', result=[])

        res = []
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询这这个技能有那些人会
                    session_result = await session.execute(
                        select(User.id, UserGroup.user_group_nickname).
                        join(UserSkill).join(UserGroup).
                        where(User.id == UserSkill.user_id).
                        where(User.id == UserGroup.user_id).
                        where(UserSkill.skill_id == skill_id_result.result).
                        where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    user_res = [(x[0], x[1]) for x in session_result.all()]
                    # 查这个人是不是空闲
                    for user_id, nickname in user_res:
                        session_result = await session.execute(
                            select(Vacation.status).where(Vacation.user_id == user_id)
                        )
                        # 如果空闲则把这个人昵称放进结果列表里面
                        if session_result.scalar_one() == 0:
                            res.append(nickname)
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def vacation_member_list(self) -> Result.ListResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 查询所有没有假的人
                    session_result = await session.execute(
                        select(UserGroup.user_group_nickname, Vacation.stop_at).
                        select_from(UserGroup).join(User).
                        where(UserGroup.user_id == User.id).
                        where(User.id == Vacation.user_id).
                        where(Vacation.status == 1).
                        where(UserGroup.group_id == bot_group_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def init_member_status(self) -> Result.IntResult:
        member_list_res = await self.member_list()
        for user_qq, nickname in member_list_res.result:
            user = DBUser(user_id=user_qq)
            user_status_res = await user.status()
            if user_status_res.error:
                await user.status_set(status=0)
        return Result.IntResult(error=False, info='ignore', result=0)

    async def subscription_list(self) -> Result.ListResult:
        """
        :return: Result: List[Tuple[sub_type, sub_id, up_name]]
        """
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_type, Subscription.sub_id, Subscription.up_name).
                        join(GroupSub).
                        where(Subscription.id == GroupSub.sub_id).
                        where(GroupSub.group_id == bot_group_id_result.result)
                    )
                    res = [(x[0], x[1], x[2]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_list_by_type(self, sub_type: int) -> Result.ListResult:
        """
        :param sub_type: 订阅类型
        :return: Result: List[Tuple[sub_id, up_name]]
        """
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Subscription.sub_id, Subscription.up_name).
                        join(GroupSub).
                        where(Subscription.sub_type == sub_type).
                        where(Subscription.id == GroupSub.sub_id).
                        where(GroupSub.group_id == bot_group_id_result.result)
                    )
                    res = [(x[0], x[1]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def subscription_add(self, sub: DBSubscription, group_sub_info: str = None) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(GroupSub).
                            where(GroupSub.group_id == bot_group_id_result.result).
                            where(GroupSub.sub_id == sub_id_result.result)
                        )
                        # 订阅关系已存在, 更新信息
                        exist_subscription = session_result.scalar_one()
                        exist_subscription.group_sub_info = group_sub_info
                        exist_subscription.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        subscription = GroupSub(sub_id=sub_id_result.result, group_id=bot_group_id_result.result,
                                                group_sub_info=group_sub_info, created_at=datetime.now())
                        session.add(subscription)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_del(self, sub: DBSubscription) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        sub_id_result = await sub.id()
        if sub_id_result.error:
            return Result.IntResult(error=True, info='Subscription not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).
                        where(GroupSub.group_id == bot_group_id_result.result).
                        where(GroupSub.sub_id == sub_id_result.result)
                    )
                    exist_subscription = session_result.scalar_one()
                    await session.delete(exist_subscription)
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

    async def subscription_clear(self) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).where(GroupSub.group_id == bot_group_id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def subscription_clear_by_type(self, sub_type: int) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSub).join(Subscription).
                        where(GroupSub.sub_id == Subscription.id).
                        where(Subscription.sub_type == sub_type).
                        where(GroupSub.group_id == bot_group_id_result.result)
                    )
                    for exist_group_sub in session_result.scalars().all():
                        await session.delete(exist_group_sub)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_list(self) -> Result.ListResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(EmailBox.address).
                        join(GroupEmailBox).
                        where(EmailBox.id == GroupEmailBox.email_box_id).
                        where(GroupEmailBox.group_id == bot_group_id_result.result)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def mailbox_add(self, mailbox: DBEmailBox, mailbox_info: str = None) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        mailbox_id_result = await mailbox.id()
        if mailbox_id_result.error:
            return Result.IntResult(error=True, info='Mailbox not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(GroupEmailBox).
                            where(GroupEmailBox.group_id == bot_group_id_result.result).
                            where(GroupEmailBox.email_box_id == mailbox_id_result.result)
                        )
                        # 群邮箱已存在, 更新信息
                        exist_mailbox = session_result.scalar_one()
                        exist_mailbox.box_info = mailbox_info
                        exist_mailbox.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_mailbox = GroupEmailBox(email_box_id=mailbox_id_result.result,
                                                    group_id=bot_group_id_result.result,
                                                    box_info=mailbox_info, created_at=datetime.now())
                        session.add(new_mailbox)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def mailbox_del(self, mailbox: DBEmailBox) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        mailbox_id_result = await mailbox.id()
        if mailbox_id_result.error:
            return Result.IntResult(error=True, info='Mailbox not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupEmailBox).
                        where(GroupEmailBox.group_id == bot_group_id_result.result).
                        where(GroupEmailBox.email_box_id == mailbox_id_result.result)
                    )
                    exist_mailbox = session_result.scalar_one()
                    await session.delete(exist_mailbox)
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

    async def mailbox_clear(self) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupEmailBox).where(GroupEmailBox.group_id == bot_group_id_result.result)
                    )
                    for exist_mailbox in session_result.scalars().all():
                        await session.delete(exist_mailbox)
                await session.commit()
                result = Result.IntResult(error=False, info='Success', result=0)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def setting_list(self) -> Result.ListResult:
        """
        :return: Result: List[Tuple[setting_name, main_config, secondary_config, extra_config]]
        """
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.ListResult(error=True, info='BotGroup not exist', result=[])

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(GroupSetting.setting_name, GroupSetting.main_config,
                               GroupSetting.secondary_config, GroupSetting.extra_config).
                        where(GroupSetting.group_id == bot_group_id_result.result)
                    )
                    res = [(x[0], x[1], x[2], x[3]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    async def setting_get(self, setting_name: str) -> Result.TextTupleResult:
        """
        :param setting_name: 配置名称
        :return: Result: Tuple[main_config, secondary_config, extra_config]
        """
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.TextTupleResult(error=True, info='BotGroup not exist', result=('', '', ''))

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(GroupSetting.main_config, GroupSetting.secondary_config, GroupSetting.extra_config).
                        where(GroupSetting.setting_name == setting_name).
                        where(GroupSetting.group_id == bot_group_id_result.result)
                    )
                    main, second, extra = session_result.one()
                    result = Result.TextTupleResult(error=False, info='Success', result=(main, second, extra))
                except NoResultFound:
                    result = Result.TextTupleResult(error=True, info='NoResultFound', result=('', '', ''))
                except MultipleResultsFound:
                    result = Result.TextTupleResult(error=True, info='MultipleResultsFound', result=('', '', ''))
                except Exception as e:
                    result = Result.TextTupleResult(error=True, info=repr(e), result=('', '', ''))
        return result

    async def setting_set(
            self,
            setting_name: str,
            main_config: str,
            *,
            secondary_config: str = 'None',
            extra_config: str = 'None',
            setting_info: str = 'None') -> Result.IntResult:

        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(GroupSetting).
                            where(GroupSetting.setting_name == setting_name).
                            where(GroupSetting.group_id == bot_group_id_result.result)
                        )
                        # 已存在, 更新信息
                        exist_setting = session_result.scalar_one()
                        exist_setting.main_config = main_config
                        exist_setting.secondary_config = secondary_config
                        exist_setting.extra_config = extra_config
                        exist_setting.setting_info = setting_info
                        exist_setting.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_setting = GroupSetting(group_id=bot_group_id_result.result, setting_name=setting_name,
                                                   main_config=main_config, secondary_config=secondary_config,
                                                   extra_config=extra_config, setting_info=setting_info,
                                                   created_at=datetime.now())
                        session.add(new_setting)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def setting_del(self, setting_name: str) -> Result.IntResult:
        bot_group_id_result = await self.bot_group_id()
        if bot_group_id_result.error:
            return Result.IntResult(error=True, info='BotGroup not exist', result=-1)

        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(
                        select(GroupSetting).
                        where(GroupSetting.setting_name == setting_name).
                        where(GroupSetting.group_id == bot_group_id_result.result)
                    )
                    exist_setting = session_result.scalar_one()
                    await session.delete(exist_setting)
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
